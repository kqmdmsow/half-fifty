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
import os

from typing import List, Literal, Optional

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.graph import run_pipeline
from src.ocr import SUPPORTED_IMAGE_TYPES, OcrUnavailableError, document_parse_text
from src.pdf_extract import extract_text_from_pdf
from src.state import PipelineState
from src.stream import stream_analysis

# 2025 체류외국인(중국·베트남·네팔·우즈벡·캄보디아·태국 순)·E-9(캄보디아·네팔·
# 베트남 상위)·유학생(우즈벡·몽골·네팔·미얀마) 통계 기반 16개 언어
Language = Literal[
    "ko", "en", "zh", "vi", "th", "id", "tl", "ne",
    "km", "my", "mn", "uz", "si", "bn", "ru", "ja",
]

app = FastAPI(title="Half-Fifty Agent Service", version="0.1.0")

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


class AnalyzeResponse(BaseModel):
    clause_count: int
    parse_warnings: List[str] = []  # 추출 누락 가능성 고지 (자문 §2)
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
        )
        for r in state["adapted_results"]
    ]

    # judge_scores에는 점수(float) 외에 rationale(dict, 콘솔 로그 참고용)이 섞여
    # 있다 — 백엔드 DTO는 Map<String, Double>이므로 숫자만 내보낸다.
    judge_scores = {k: v for k, v in state["judge_scores"].items() if isinstance(v, (int, float))}

    return AnalyzeResponse(
        clause_count=len(state["clauses"]),
        parse_warnings=state.get("parse_warnings", []),
        retry_count=state["retry_count"],
        needs_review=state["needs_review"],
        judge_scores=judge_scores,
        results=results,
    )


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


@app.post("/analyze-pdf", response_model=AnalyzeResponse)
async def analyze_pdf(
    file: UploadFile,
    persona: Literal["adult", "senior", "foreigner"] = Form("adult"),
    language: Language = Form("ko"),
) -> AnalyzeResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="application/pdf 파일만 지원합니다.")

    pdf_bytes = await file.read()

    try:
        text = extract_text_from_pdf(pdf_bytes)
    except ValueError as exc:
        # 텍스트 레이어 없음(스캔본) → OCR 폴백 (Upstage Document Parse)
        try:
            text = document_parse_text(pdf_bytes, file.filename or "upload.pdf")
        except OcrUnavailableError as ocr_exc:
            raise HTTPException(
                status_code=422, detail=f"{exc} / OCR 폴백 실패: {ocr_exc}") from ocr_exc

    state = run_pipeline(text, persona=persona, language=language or "ko")
    return _state_to_response(state)


@app.post("/analyze-image", response_model=AnalyzeResponse)
async def analyze_image(
    file: UploadFile,
    persona: Literal["adult", "senior", "foreigner"] = Form("adult"),
    language: Language = Form("ko"),
) -> AnalyzeResponse:
    """계약서 사진(jpg/png/webp) 분석 — Upstage Document Parse OCR 경유.

    타깃 사용자(고령층)의 자연스러운 입력 수단. 표 구조를 인식하므로
    별표·수수료율 표가 있는 계약서 사진에도 대응한다.
    """
    if file.content_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="jpg/png/webp 이미지만 지원합니다.")

    image_bytes = await file.read()
    try:
        text = document_parse_text(image_bytes, file.filename or "upload.png")
    except OcrUnavailableError as exc:
        raise HTTPException(status_code=422, detail=f"사진에서 글자를 읽지 못했습니다: {exc}") from exc

    state = run_pipeline(text, persona=persona, language=language or "ko")
    return _state_to_response(state)
