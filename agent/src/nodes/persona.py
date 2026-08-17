"""Persona Adaptation Agent: 4종 출력을 사용자 페르소나에 맞게 변환.

MVP 페르소나 2종:
- adult  : 일반 성인 (표준 설명)
- senior : 고령층 (짧은 문장, 일상 어휘, 예시 중심)

src/prompts/persona_adult.txt / persona_senior.txt로 MODEL_WORKER를 호출해
explanation만 다시 쓴다. 나머지 필드(위험 여부/근거/질문)는 그대로 유지한다.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

from src.llm import get_worker_llm, invoke_json
from src.state import AnalysisResult, PipelineState

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_MAX_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", "5"))  # analysis_node와 동일 (env로 상향 가능)

_TEMPLATES = {
    "adult": (PROMPTS_DIR / "persona_adult.txt").read_text(encoding="utf-8"),
    "senior": (PROMPTS_DIR / "persona_senior.txt").read_text(encoding="utf-8"),
    "foreigner": (PROMPTS_DIR / "persona_foreigner.txt").read_text(encoding="utf-8"),
}

# 지원 출력 언어 — persona_foreigner 프롬프트의 {language}에 들어갈 자연어 이름.
LANGUAGE_NAMES = {
    "ko": "한국어(쉬운 표현)",
    "en": "English",
    "zh": "简体中文",
    "vi": "Tiếng Việt",
}


def _adapt(result: AnalysisResult, persona: str, language: str = "ko") -> AnalysisResult:
    template = _TEMPLATES.get(persona, _TEMPLATES["adult"])
    analysis_result_json = json.dumps(dict(result), ensure_ascii=False)
    prompt = template.replace("{analysis_result}", analysis_result_json)
    prompt = prompt.replace("{language}", LANGUAGE_NAMES.get(language, language))

    llm = get_worker_llm()
    try:
        data = invoke_json(llm, prompt)
        explanation = data["explanation"]
    except Exception as exc:
        # 페르소나 적응 실패는 치명적이지 않다 — 원문 explanation을 그대로 쓰고
        # 파이프라인은 계속 간다 (analysis/judge와 동일한 방어 원칙, PR#43 참조).
        print(f"[Persona] {result['clause_id']} 적응 실패, 원본 설명 유지: {exc}")
        explanation = result["explanation"]

    adapted = dict(result)
    adapted["explanation"] = explanation
    return adapted  # type: ignore[return-value]


def persona_node(state: PipelineState) -> dict:
    """LangGraph 노드: analysis_results + persona(+language) -> adapted_results.

    조항별 적응은 독립이므로 스레드 풀로 병렬 호출한다 (순서 보존).
    템플릿이 캐시 최소 토큰에 못 미쳐 프롬프트 캐싱은 적용하지 않는다.
    """
    persona = state["persona"]
    language = state.get("language", "ko") or "ko"
    with ThreadPoolExecutor(max_workers=_MAX_CONCURRENCY) as pool:
        adapted: List[AnalysisResult] = list(
            pool.map(lambda r: _adapt(r, persona, language), state["analysis_results"])
        )
    return {"adapted_results": adapted}
