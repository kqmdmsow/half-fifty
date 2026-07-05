"""Persona Adaptation Agent: 4종 출력을 사용자 페르소나에 맞게 변환.

MVP 페르소나 2종:
- adult  : 일반 성인 (표준 설명)
- senior : 고령층 (짧은 문장, 일상 어휘, 예시 중심)

현재는 더미 구현. LLM 연동 시 persona별 프롬프트 파일 사용:
- src/prompts/persona_adult.txt
- src/prompts/persona_senior.txt
"""

from pathlib import Path
from typing import List

from src.state import AnalysisResult, PipelineState

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _adapt_dummy(result: AnalysisResult, persona: str) -> AnalysisResult:
    if persona == "senior":
        prefix = "[고령층 맞춤·더미] 쉽게 말씀드리면, "
    else:
        prefix = "[일반 성인·더미] "

    adapted = dict(result)
    adapted["explanation"] = prefix + result["explanation"]
    return adapted  # type: ignore[return-value]


def persona_node(state: PipelineState) -> dict:
    """LangGraph 노드: analysis_results + persona -> adapted_results.

    TODO(민제): LLM 연동 시 페르소나별 프롬프트로 재작성 요청.
    """
    persona = state["persona"]
    adapted: List[AnalysisResult] = [
        _adapt_dummy(r, persona) for r in state["analysis_results"]
    ]
    return {"adapted_results": adapted}
