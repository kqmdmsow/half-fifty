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
# 영문 병기는 모델이 언어를 확실히 인식하도록 하기 위함 (특히 저자원 언어).
LANGUAGE_NAMES = {
    "ko": "한국어(쉬운 표현)",
    "en": "English",
    "zh": "简体中文 (Simplified Chinese)",
    "vi": "Tiếng Việt (Vietnamese)",
    "th": "ภาษาไทย (Thai)",
    "id": "Bahasa Indonesia (Indonesian)",
    "tl": "Filipino/Tagalog",
    "ne": "नेपाली (Nepali)",
    "km": "ភាសាខ្មែរ (Khmer)",
    "my": "မြန်မာဘာသာ (Burmese)",
    "mn": "Монгол хэл (Mongolian)",
    "uz": "Oʻzbek tili (Uzbek)",
    "si": "සිංහල (Sinhala)",
    "bn": "বাংলা (Bengali)",
    "ru": "Русский (Russian)",
    "ja": "日本語 (Japanese)",
}


def _adapt(
    result: AnalysisResult, persona: str, language: str = "ko", clause_text: str = ""
) -> tuple[AnalysisResult, dict | None]:
    """explanation 재작성 + (foreigner·비한국어일 때) 원문·질문 번역.

    반환: (adapted_result, translation | None)
    translation = {"original_text_translated": str, "check_questions_translated": [str]}

    번역은 adapted_result에 섞지 않고 분리해서 반환한다 — adapted_results는
    Judge 입력으로 들어가는데, 검증된 채점 동작에 낯선 필드를 추가하지 않기 위함.
    """
    # 언어가 한국어가 아니면 페르소나와 무관하게 번역 템플릿을 쓴다 —
    # 헤더의 전역 언어 선택이 페르소나 선택보다 우선하는 UX.
    if language != "ko":
        template = _TEMPLATES["foreigner"]
    else:
        template = _TEMPLATES.get(persona, _TEMPLATES["adult"])
    analysis_result_json = json.dumps(dict(result), ensure_ascii=False)
    prompt = template.replace("{analysis_result}", analysis_result_json)
    prompt = prompt.replace("{clause_text}", clause_text)
    prompt = prompt.replace("{language}", LANGUAGE_NAMES.get(language, language))

    translation = None
    try:
        data = invoke_json(llm := get_worker_llm(), prompt)
        explanation = data["explanation"]
        if language != "ko":
            questions = data.get("check_questions_translated")
            translation = {
                "original_text_translated": data.get("original_text_translated") or "",
                "check_questions_translated": questions if isinstance(questions, list) else [],
            }
    except Exception as exc:
        # 페르소나 적응 실패는 치명적이지 않다 — 원문 explanation을 그대로 쓰고
        # 파이프라인은 계속 간다 (analysis/judge와 동일한 방어 원칙, PR#43 참조).
        print(f"[Persona] {result['clause_id']} 적응 실패, 원본 설명 유지: {exc}")
        explanation = result["explanation"]

    adapted = dict(result)
    adapted["explanation"] = explanation
    return adapted, translation  # type: ignore[return-value]


def persona_node(state: PipelineState) -> dict:
    """LangGraph 노드: analysis_results + persona(+language) -> adapted_results + translations.

    조항별 적응은 독립이므로 스레드 풀로 병렬 호출한다 (순서 보존).
    템플릿이 캐시 최소 토큰에 못 미쳐 프롬프트 캐싱은 적용하지 않는다.
    """
    persona = state["persona"]
    language = state.get("language", "ko") or "ko"
    clause_text = {c["clause_id"]: c["text"] for c in state.get("clauses", [])}
    with ThreadPoolExecutor(max_workers=_MAX_CONCURRENCY) as pool:
        pairs = list(
            pool.map(
                lambda r: _adapt(r, persona, language, clause_text.get(r["clause_id"], "")),
                state["analysis_results"],
            )
        )
    adapted: List[AnalysisResult] = [p[0] for p in pairs]
    translations = {
        a["clause_id"]: tr for (a, tr) in pairs if tr is not None
    }
    return {"adapted_results": adapted, "translations": translations}
