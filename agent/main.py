"""Agent Service API (FastAPI).

Spring Boot 백엔드(동훈)가 호출하는 진입점.
PDF 업로드(/analyze-pdf)는 프론트에서 직접 호출한다 (CORS 허용).

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

from typing import List, Literal

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.graph import run_pipeline
from src.pdf_extract import extract_text_from_pdf
from src.state import PipelineState

app = FastAPI(title="Half-Fifty Agent Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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

    return AnalyzeResponse(
        clause_count=len(state["clauses"]),
        retry_count=state["retry_count"],
        needs_review=state["needs_review"],
        judge_scores=dict(state["judge_scores"]),
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
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    state = run_pipeline(text, persona=persona)
    return _state_to_response(state)
