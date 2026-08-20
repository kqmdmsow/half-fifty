"""사용자 트리거 재설명 (#76) — judge 검증 분기를 통과한 결과만 반환.

프로젝트 핵심 차별점(judge 게이팅)이 지금은 자동으로만 일어난다 — 이 모듈은
사용자가 "더 쉽게/더 자세히"를 눌렀을 때 재생성→judge 채점→게이트 통과분만
화면에 반영되게 해서, "AI가 자기 답을 검증한다"를 사용자 손끝에서 체험하게
만든다 (자문 §3 그래프 분기의 살아있는 사용례, §6 이해 회복 경로).

불변 조건:
- **판정 불변**: explanation만 재생성. risk_level·risk_type·근거·질문은
  건드리지 않는다 (w/o-persona ablation 20/20 — 표현이 판정을 바꾸지 않음).
- **게이트 동일**: 본 파이프라인과 같은 judge_node·FAITHFULNESS_MIN·
  JUDGE_THRESHOLD 상수를 그대로 쓴다. 통과 실패 시 1회 재생성, 그래도
  실패하면 ok=False — 프론트는 기존 설명을 유지한다 (틀린 설명을 보여주지
  않는 것이 기능의 존재 이유).
"""

import json
import logging
from pathlib import Path
from typing import Optional

from src.llm import get_worker_llm, invoke_json
from src.nodes.judge import judge_node
from src.state import FAITHFULNESS_MIN, JUDGE_THRESHOLD, judge_score_avg

logger = logging.getLogger(__name__)

_PROMPT = (Path(__file__).parent / "prompts" / "reexplain.txt").read_text(encoding="utf-8")

_MODES = {
    "easier": {
        "label": "더 쉽게 설명해줘",
        "instruction": (
            "- 문장을 절반 길이로 짧게 끊고, 법률 용어 대신 일상어를 씁니다.\n"
            "- 구체적인 생활 예시를 1개 덧붙입니다 (사실관계를 새로 만들지는 않음).\n"
            "- 어려운 개념은 '쉽게 말하면 ~' 형태로 다시 풀어 줍니다."
        ),
    },
    "detailed": {
        "label": "더 자세히 설명해줘",
        "instruction": (
            "- 기존 설명의 각 주장에 조항 원문의 근거 문구를 연결해 확장합니다.\n"
            "- 왜 그렇게 판단되는지 단계별로 풀어 씁니다.\n"
            "- 사용자가 추가로 확인하면 좋을 지점을 1가지 덧붙입니다."
        ),
    },
}

_MAX_ATTEMPTS = 2  # 최초 1회 + judge 게이트 실패 시 재생성 1회


def reexplain(
    clause_id: str,
    clause_text: str,
    analysis: dict,
    mode: str,
    persona: str = "adult",
    language: str = "ko",
) -> dict:
    """재설명 생성 + judge 게이트. 반환: {ok, explanation?, judge_scores?, retry_count}."""
    mode_conf = _MODES.get(mode)
    if not mode_conf:
        return {"ok": False, "reason": "unknown_mode", "retry_count": 0}

    prompt = (_PROMPT
              .replace("{mode_label}", mode_conf["label"])
              .replace("{mode_instruction}", mode_conf["instruction"])
              .replace("{language}", language or "ko")
              .replace("{persona}", persona)
              .replace("{clause_text}", clause_text)
              .replace("{analysis_result}", json.dumps(analysis, ensure_ascii=False)))

    last_scores: Optional[dict] = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            data = invoke_json(get_worker_llm(), prompt)
            explanation = str(data["explanation"]).strip()
            if len(explanation) < 20:
                raise ValueError("설명이 지나치게 짧음")
        except Exception as exc:
            logger.warning("%s 재설명 생성 실패(%d차): %s", clause_id, attempt + 1, type(exc).__name__)
            logger.debug("재설명 생성 실패 상세", exc_info=exc)
            continue

        # judge 게이트 — 본 파이프라인과 동일한 노드·상수 (판정 필드는 원본 유지)
        candidate = {**analysis, "clause_id": clause_id, "explanation": explanation}
        judge_state = {
            "raw_text": clause_text,
            "persona": persona,
            "clauses": [{"clause_id": clause_id, "text": clause_text}],
            "analysis_results": [candidate],
            "adapted_results": [candidate],
            "retry_count": attempt,
            "needs_review": False,
        }
        scores = judge_node(judge_state)["judge_scores"]  # type: ignore[arg-type]
        numeric = {k: v for k, v in scores.items() if isinstance(v, (int, float))}
        last_scores = numeric
        faith = scores["faithfulness"]
        avg = judge_score_avg(scores)
        if faith >= FAITHFULNESS_MIN and avg >= JUDGE_THRESHOLD:
            logger.info("%s 재설명 게이트 통과 (faith %.1f, avg %.2f, %d차)",
                        clause_id, faith, avg, attempt + 1)
            return {"ok": True, "explanation": explanation,
                    "judge_scores": numeric, "retry_count": attempt}
        logger.info("%s 재설명 게이트 미달 (faith %.1f, avg %.2f, %d차)",
                    clause_id, faith, avg, attempt + 1)

    return {"ok": False, "reason": "gate_failed",
            "judge_scores": last_scores, "retry_count": _MAX_ATTEMPTS - 1}
