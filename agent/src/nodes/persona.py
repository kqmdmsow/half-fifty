"""Persona Adaptation Agent: 4종 출력을 사용자 페르소나에 맞게 변환.

MVP 페르소나 2종:
- adult  : 일반 성인 (표준 설명)
- senior : 고령층 (짧은 문장, 일상 어휘, 예시 중심)

src/prompts/persona_adult.txt / persona_senior.txt로 MODEL_WORKER를 호출해
explanation만 다시 쓴다. 나머지 필드(위험 여부/근거/질문)는 그대로 유지한다.
"""

import json
from pathlib import Path
from typing import List

from src.llm import get_worker_llm, invoke_json
from src.state import AnalysisResult, PipelineState

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_TEMPLATES = {
    "adult": (PROMPTS_DIR / "persona_adult.txt").read_text(encoding="utf-8"),
    "senior": (PROMPTS_DIR / "persona_senior.txt").read_text(encoding="utf-8"),
}


def _adapt(result: AnalysisResult, persona: str) -> AnalysisResult:
    template = _TEMPLATES.get(persona, _TEMPLATES["adult"])
    analysis_result_json = json.dumps(dict(result), ensure_ascii=False)
    prompt = template.replace("{analysis_result}", analysis_result_json)

    llm = get_worker_llm()
    data = invoke_json(llm, prompt)

    adapted = dict(result)
    adapted["explanation"] = data["explanation"]
    return adapted  # type: ignore[return-value]


def persona_node(state: PipelineState) -> dict:
    """LangGraph 노드: analysis_results + persona -> adapted_results."""
    persona = state["persona"]
    adapted: List[AnalysisResult] = [
        _adapt(r, persona) for r in state["analysis_results"]
    ]
    return {"adapted_results": adapted}
