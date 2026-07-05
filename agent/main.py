"""Agent Service API (FastAPI).

Spring Boot 백엔드(동훈)가 호출하는 진입점.

실행:
    cd agent
    source .venv/bin/activate
    uvicorn main:app --reload --port 8000

테스트:
    curl -X POST http://localhost:8000/analyze \
      -H "Content-Type: application/json" \
      -d '{"text": "제1조 임차인은 보증금을 지급한다.", "persona": "adult"}'
"""

from typing import List, Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.graph import run_pipeline

app = FastAPI(title="Half-Fifty Agent Service", version="0.1.0")


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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    state = run_pipeline(req.text, persona=req.persona)

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
