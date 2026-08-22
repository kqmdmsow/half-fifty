"""Agent Service API (FastAPI).

Spring Boot 백엔드(동훈)가 호출하는 진입점.
PDF 업로드(/analyze-pdf)도 백엔드 프록시를 거친다 (자문 §7 — 직통 제거).

실행:
    cd agent
    source .venv/bin/activate
    uvicorn main:app --reload --port 8000

테스트:
    curl -X POST http://localhost:8000/analyze \
      -H "Content-Type: application/json" \
      -d '{"text": "제1조 임차인은 보증금을 지급한다.", "persona": "adult"}'

    curl -X POST http://localhost:8000/analyze-pdf \
      -F "file=@contract.pdf" -F "persona=adult"
"""

import json
import logging
import os
import time

from typing import List, Literal, Optional

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.case_footnotes import CaseFootnote, get_related_cases
from src.file_validation import MAX_UPLOAD_BYTES, is_pdf_magic, sniff_image_type
from src.graph import run_pipeline
from src.learn_content import localized_learn
from src.ocr import SUPPORTED_IMAGE_TYPES, OcrUnavailableError, document_parse_text
from src.pdf_extract import extract_text_from_pdf
from src.quiz import generate_quiz
from src.reexplain import reexplain
from src.state import PipelineState
from src.stream import stream_analysis

# 2025 체류외국인(중국·베트남·네팔·우즈벡·캄보디아·태국 순)·E-9(캄보디아·네팔·
# 베트남 상위)·유학생(우즈벡·몽골·네팔·미얀마) 통계 기반 16개 언어
Language = Literal[
    "ko", "en", "zh", "vi", "th", "id", "tl", "ne",
    "km", "my", "mn", "uz", "si", "bn", "ru", "ja",
]

# 운영 로그 표준화 (#80, 자문 §7 '오류 및 접근 기록 관리').
# 원칙: 계약 내용·파일명 등 개인정보는 로그에 남기지 않는다 — 경로·상태·소요시간만.
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
_access_logger = logging.getLogger("access")

app = FastAPI(title="Jomokjomok (조목조목) Agent Service", version="0.1.0")


@app.middleware("http")
async def access_log(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    # 스트리밍 응답은 헤더 반환 시점까지의 시간이다 (본문 전송은 이후 계속됨)
    _access_logger.info(
        "%s %s -> %d (%.2fs)",
        request.method, request.url.path, response.status_code,
        time.perf_counter() - start,
    )
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="계약서 원문 텍스트")
    persona: Literal["adult", "senior", "foreigner"] = Field("adult", description="사용자 페르소나")
    # Optional — 백엔드(Java record)가 필드를 안 보내거나 null을 보내도 허용
    language: Optional[Language] = Field("ko", description="설명 출력 언어 (foreigner 페르소나용)")
    domain: str = Field("", description="사용자가 선택한 문서 유형 (선택 입력, 예: 주택임대차)")


class ClauseResult(BaseModel):
    clause_id: str
    original_text: str
    explanation: str
    risk_level: str
    risk_type: str
    risk_evidence: str
    check_questions: List[str]
    # 비한국어 언어 선택 시에만 채워짐 (한국어 원문·질문은 그대로 유지 + 번역 병기)
    original_text_translated: Optional[str] = None
    check_questions_translated: Optional[List[str]] = None
    risk_evidence_translated: Optional[str] = None
    # 시그니처 기능 ① 실제 사건 각주 (#91) — 표시 전용, Judge 채점에는
    # 안 쓰인다 (state에 안 실리고 여기서 응답 조립 시점에만 조회).
    related_cases: List[CaseFootnote] = []


class AnalyzeResponse(BaseModel):
    clause_count: int
    parse_warnings: List[str] = []
    # 경고별 기계 판독 코드 (#86-② — 인덱스가 parse_warnings와 정렬, 미분류는 None)
    parse_warning_codes: List[Optional[str]] = []  # 추출 누락 가능성 고지 (자문 §2)
    retry_count: int
    needs_review: bool
    judge_scores: dict
    results: List[ClauseResult]


def _state_to_response(state: PipelineState) -> AnalyzeResponse:
    clause_text = {c["clause_id"]: c["text"] for c in state["clauses"]}
    translations = state.get("translations", {})
    results = [
        ClauseResult(
            clause_id=r["clause_id"],
            original_text=clause_text.get(r["clause_id"], ""),
            explanation=r["explanation"],
            risk_level=r["risk_level"],
            risk_type=r["risk_type"],
            risk_evidence=r["risk_evidence"],
            check_questions=r["check_questions"],
            original_text_translated=translations.get(r["clause_id"], {}).get("original_text_translated"),
            check_questions_translated=translations.get(r["clause_id"], {}).get("check_questions_translated"),
            risk_evidence_translated=translations.get(r["clause_id"], {}).get("risk_evidence_translated"),
            related_cases=get_related_cases(r["risk_type"]),
        )
        for r in state["adapted_results"]
    ]

    # judge_scores에는 점수(float) 외에 rationale(dict, 콘솔 로그 참고용)이 섞여
    # 있다 — 백엔드 DTO는 Map<String, Double>이므로 숫자만 내보낸다.
    judge_scores = {k: v for k, v in state["judge_scores"].items() if isinstance(v, (int, float))}

    from src.warning_codes import classify_all

    return AnalyzeResponse(
        clause_count=len(state["clauses"]),
        parse_warnings=state.get("parse_warnings", []),
        parse_warning_codes=classify_all(state.get("parse_warnings", [])),
        retry_count=state["retry_count"],
        needs_review=state["needs_review"],
        judge_scores=judge_scores,
        results=results,
    )


class QuizRequest(BaseModel):
    """이해 확인 퀴즈 생성 요청 (#92) — 프론트가 분석 결과에서 발췌해 보낸다."""

    items: List[dict] = Field(..., description="위험도순 조항 분석 발췌 (최대 3개 사용)")
    persona: Literal["adult", "senior", "foreigner"] = "adult"
    language: Optional[Language] = "ko"


class ReexplainRequest(BaseModel):
    """사용자 트리거 재설명 (#76) — explanation만 재생성, 판정 불변."""

    clause_id: str
    clause_text: str = Field(..., description="조항 원문 (judge faithfulness 채점 기준)")
    analysis: dict = Field(..., description="기존 분석 결과 (risk_level 등 판정 필드 포함)")
    mode: Literal["easier", "detailed"]
    persona: Literal["adult", "senior", "foreigner"] = "adult"
    language: Optional[Language] = "ko"


@app.post("/quiz")
def quiz(req: QuizRequest) -> dict:
    """객관식 3문항 생성 — 코드 가드 통과분만, 미달 시 빈 목록 (src/quiz.py)."""
    return {"questions": generate_quiz(req.items, req.persona, req.language or "ko")}  # type: ignore[arg-type]


@app.post("/reexplain")
def reexplain_endpoint(req: ReexplainRequest) -> dict:
    """judge 게이트 통과분만 반환 — 실패 시 ok=False (프론트는 기존 설명 유지)."""
    return reexplain(req.clause_id, req.clause_text, req.analysis,
                     req.mode, req.persona, req.language or "ko")


@app.get("/learn")
def learn(language: str = "ko") -> dict:
    """교육 콘텐츠 단일 원천 — 정적 번역본이 있는 언어는 번역해서 반환 (#104).

    내장 챗봇(/learn-chat, #103)은 세션당 대화 횟수 상한과 인젝션 방어
    (#131 규칙 탐지기 재사용 또는 #149식 프롬프트 방어 블록) 조건을 걸고
    나서 별도 PR로 합류한다 — 지금은 정적 콘텐츠만 노출.
    """
    return localized_learn(language)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    state = run_pipeline(req.text, persona=req.persona, language=req.language or "ko", domain=req.domain)
    return _state_to_response(state)


@app.post("/analyze-stream")
def analyze_stream(req: AnalyzeRequest) -> StreamingResponse:
    """조항별 점진 스트리밍 (NDJSON). 이벤트 계약은 src/stream.py docstring 참조.

    조항 이벤트는 Judge 검증 전 결과 — 클라이언트는 '검증 중'으로 표시하고
    judge 이벤트로 확정해야 한다.
    """

    def gen():
        for event in stream_analysis(req.text, req.persona, req.language or "ko", req.domain):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


def _ndjson(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"


@app.post("/analyze-file-stream")
async def analyze_file_stream(
    file: UploadFile,
    persona: Literal["adult", "senior", "foreigner"] = Form("adult"),
    language: Language = Form("ko"),
    domain: str = Form(""),
) -> StreamingResponse:
    """파일(PDF·사진) 업로드의 조항별 점진 스트리밍 (NDJSON).

    이벤트 계약은 /analyze-stream과 동일하고, 맨 앞에 추출 단계 이벤트가 붙는다:
      {"event":"extract"}                              # 텍스트 추출(OCR 포함) 시작
      {"event":"error","status":422,"message":...}     # 추출 실패 시 — 스트림이
                                                       # 이미 열린 뒤라 HTTP 상태
                                                       # 대신 이벤트로 알린다
    형식·용량 검증은 스트림을 열기 전이므로 기존 파일 엔드포인트와 동일하게
    HTTPException으로 응답한다. Judge 게이트(재시도·needs_review)는 텍스트
    스트리밍과 완전히 같은 stream_analysis를 재사용한다.
    """
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="파일은 10MB 이하만 지원합니다.")
    pdf = is_pdf_magic(raw)
    if not pdf and sniff_image_type(raw) is None:
        raise HTTPException(status_code=415, detail="PDF 또는 jpg/png/webp 파일만 지원합니다.")
    filename = file.filename or ("upload.pdf" if pdf else "upload.png")

    def gen():
        yield _ndjson({"event": "extract"})
        try:
            if pdf:
                try:
                    text = extract_text_from_pdf(raw)
                except ValueError:
                    # 텍스트 레이어 없음(스캔본) → OCR 폴백 (Upstage Document Parse)
                    text = document_parse_text(raw, filename)
            else:
                text = document_parse_text(raw, filename)
        except (OcrUnavailableError, ValueError) as exc:
            yield _ndjson({"event": "error", "status": 422,
                           "message": f"파일에서 글자를 읽지 못했습니다: {exc}"})
            return
        for event in stream_analysis(text, persona, language or "ko", domain):
            yield _ndjson(event)

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.post("/analyze-pdf", response_model=AnalyzeResponse)
async def analyze_pdf(
    file: UploadFile,
    persona: Literal["adult", "senior", "foreigner"] = Form("adult"),
    language: Language = Form("ko"),
    domain: str = Form(""),
) -> AnalyzeResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="application/pdf 파일만 지원합니다.")

    pdf_bytes = await file.read()
    # 백엔드를 거치지 않고 agent를 직접 호출하는 우회 방어 (이슈 #77) —
    # Content-Type 헤더는 위조 가능하므로 실제 바이트로 재검증한다.
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF는 10MB 이하만 지원합니다.")
    if not is_pdf_magic(pdf_bytes):
        raise HTTPException(status_code=415, detail="PDF 파일이 아닙니다.")

    try:
        text = extract_text_from_pdf(pdf_bytes)
    except ValueError as exc:
        # 텍스트 레이어 없음(스캔본) → OCR 폴백 (Upstage Document Parse)
        try:
            text = document_parse_text(pdf_bytes, file.filename or "upload.pdf")
        except OcrUnavailableError as ocr_exc:
            raise HTTPException(
                status_code=422, detail=f"{exc} / OCR 폴백 실패: {ocr_exc}") from ocr_exc

    state = run_pipeline(text, persona=persona, language=language or "ko", domain=domain)
    return _state_to_response(state)


@app.post("/analyze-image", response_model=AnalyzeResponse)
async def analyze_image(
    file: UploadFile,
    persona: Literal["adult", "senior", "foreigner"] = Form("adult"),
    language: Language = Form("ko"),
    domain: str = Form(""),
) -> AnalyzeResponse:
    """계약서 사진(jpg/png/webp) 분석 — Upstage Document Parse OCR 경유.

    타깃 사용자(고령층)의 자연스러운 입력 수단. 표 구조를 인식하므로
    별표·수수료율 표가 있는 계약서 사진에도 대응한다.
    """
    if file.content_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="jpg/png/webp 이미지만 지원합니다.")

    image_bytes = await file.read()
    # 백엔드를 거치지 않고 agent를 직접 호출하는 우회 방어 (이슈 #77) —
    # Content-Type 헤더는 위조 가능하므로 실제 바이트로 재검증한다.
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="이미지는 10MB 이하만 지원합니다.")
    if sniff_image_type(image_bytes) is None:
        raise HTTPException(status_code=415, detail="jpg/png/webp 이미지가 아닙니다.")
    try:
        text = document_parse_text(image_bytes, file.filename or "upload.png")
    except OcrUnavailableError as exc:
        raise HTTPException(status_code=422, detail=f"사진에서 글자를 읽지 못했습니다: {exc}") from exc

    state = run_pipeline(text, persona=persona, language=language or "ko", domain=domain)
    return _state_to_response(state)
