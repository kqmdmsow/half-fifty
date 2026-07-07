"""Analysis Agent: 조항별 4종 출력 생성.

① 쉬운 설명 ② 위험 여부/유형 ③ 위험 근거 ④ 확인 질문

src/prompts/analysis.txt 프롬프트로 MODEL_WORKER를 호출한다.
JSON 파싱 실패 시 1회 재시도하고, 그래도 실패하면 "주의" + 수동 확인 안내로 폴백한다.
"""

from pathlib import Path
from typing import List

from src.llm import get_worker_llm, invoke_json
from src.state import AnalysisResult, PipelineState

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "analysis.txt"
_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

_PARSE_ATTEMPTS = 2  # 최초 시도 + 재시도 1회
_FALLBACK_EVIDENCE = "분석 실패 (수동 확인 필요)"


def _analyze_clause(clause_id: str, text: str) -> AnalysisResult:
    prompt = _PROMPT_TEMPLATE.replace("{clause_text}", text)
    llm = get_worker_llm()

    for attempt in range(_PARSE_ATTEMPTS):
        try:
            data = invoke_json(llm, prompt)
            return AnalysisResult(
                clause_id=clause_id,
                explanation=data["explanation"],
                risk_level=data["risk_level"],
                risk_type=data["risk_type"],
                risk_evidence=data["risk_evidence"],
                check_questions=data["check_questions"],
            )
        except Exception as exc:  # JSON 파싱 실패, 키 누락 등
            if attempt + 1 == _PARSE_ATTEMPTS:
                print(f"[Analysis] {clause_id} 분석 실패, 폴백 처리: {exc}")

    return AnalysisResult(
        clause_id=clause_id,
        explanation=text,
        risk_level="주의",
        risk_type="해당 없음",
        risk_evidence=_FALLBACK_EVIDENCE,
        check_questions=[],
    )


def analysis_node(state: PipelineState) -> dict:
    """LangGraph 노드: clauses -> analysis_results."""
    results: List[AnalysisResult] = [
        _analyze_clause(c["clause_id"], c["text"]) for c in state["clauses"]
    ]
    return {"analysis_results": results}
