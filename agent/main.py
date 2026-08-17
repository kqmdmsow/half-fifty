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

import os

from typing import List, Literal

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.graph import run_pipeline
from src.ocr import SUPPORTED_IMAGE_TYPES, OcrUnavailableError, document_parse_text
from src.pdf_extract import extract_text_from_pdf
from src.state import PipelineState

app = FastAPI(title="Half-Fifty Agent Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="계약서 원문 텍스트")
    persona: Literal["adult", "senior"] = Field("adult", description="사용자 페르소나")


class ClauseResult(BaseModel):
    clause_id: str
    original_text: str
    explanation: str
    risk_level: str
    risk_type: str
    risk_evidence: str
    check_questions: List[str]


class AnalyzeResponse(BaseModel):
    clause_count: int
    parse_warnings: List[str] = []  # 추출 누락 가능성 고지 (자문 §2)
    retry_count: int
    needs_review: bool
    judge_scores: dict
    results: List[ClauseResult]


def _state_to_response(state: PipelineState) -> AnalyzeResponse:
    clause_text = {c["clause_id"]: c["text"] for c in state["clauses"]}
    results = [
        ClauseResult(
            clause_id=r["clause_id"],
            original_text=clause_text.get(r["clause_id"], ""),
            explanation=r["explanation"],
            risk_level=r["risk_level"],
            risk_type=r["risk_type"],
            risk_evidence=r["risk_evidence"],
            check_questions=r["check_questions"],
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
    state = run_pipeline(req.text, persona=req.persona)
    return _state_to_response(state)


@app.post("/analyze-pdf", response_model=AnalyzeResponse)
async def analyze_pdf(
    file: UploadFile,
    persona: Literal["adult", "senior"] = Form("adult"),
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

    state = run_pipeline(text, persona=persona)
    return _state_to_response(state)


@app.post("/analyze-image", response_model=AnalyzeResponse)
async def analyze_image(
    file: UploadFile,
    persona: Literal["adult", "senior"] = Form("adult"),
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

    state = run_pipeline(text, persona=persona)
    return _state_to_response(state)
