"""3문답 이해 확인 퀴즈 생성 (#92 시그니처 기능 ② — 기능이 곧 연구 도구).

설명을 읽은 사용자가 "읽었다"가 아니라 "이해했다"를 확인하는 객관식 3문항.
자문 §6(이해도 문항 정답률이 judge clarity보다 설득력 있는 지표)의 측정
도구를 제품 기능으로 구현한 것.

설계:
- **지연 생성**: 분석 파이프라인에 끼우지 않고 사용자가 퀴즈를 열 때만
  별도 호출(worker 1콜) — 주 흐름 지연·비용 0.
- **문항 품질 가드(코드 검증, LLM 불신)**: 모델이 answer_quote(정답 근거
  조각)를 explanation/risk_evidence에서 그대로 복사하게 하고, 코드가
  정규화 포함 검사(citation_check._normalize 재사용)로 실존을 확인한다.
  검증 실패 문항은 폐기, 생존 문항이 2개 미만이면 퀴즈 전체 미노출 —
  "없는 게 틀린 것보다 낫다"(#91과 동일 원칙).
- 판정 불변: 퀴즈는 표시 전용이며 분석 결과·judge 입력에 관여하지 않는다.
"""

import json
import logging
from pathlib import Path
from typing import List, TypedDict

from src.citation_check import _normalize
from src.llm import get_worker_llm, invoke_json
from src.schemas import QuizOutput

logger = logging.getLogger(__name__)

_PROMPT = (Path(__file__).parent / "prompts" / "quiz.txt").read_text(encoding="utf-8")

_MIN_QUESTIONS = 2  # 가드 통과 문항이 이보다 적으면 퀴즈 미노출
_MAX_SOURCE_CLAUSES = 3


class QuizItem(TypedDict):
    """프론트가 보내는 출제 재료 (조항별 분석 결과 발췌)."""

    clause_id: str
    explanation: str
    risk_level: str
    risk_type: str
    risk_evidence: str


def _grounded(question: dict, sources: dict) -> bool:
    """answer_quote가 해당 조항의 explanation/risk_evidence에 실존하는지."""
    src = sources.get(question.get("clause_id", ""))
    if not src:
        return False
    quote = _normalize(question.get("answer_quote", ""))
    if len(quote) < 10:  # 정규화 후 10자 미만이면 근거로 부족
        return False
    haystack = _normalize(src["explanation"] + " " + src["risk_evidence"])
    return quote in haystack


def generate_quiz(items: List[QuizItem], persona: str, language: str = "ko") -> List[dict]:
    """이해 확인 문항 목록 반환 (가드 통과분만, 미달 시 빈 목록).

    items는 위험도 높은 순으로 정렬돼 온다고 가정하고 상위 3개만 쓴다.
    """
    sources = {it["clause_id"]: it for it in items[:_MAX_SOURCE_CLAUSES]}
    if not sources:
        return []

    payload = json.dumps(list(sources.values()), ensure_ascii=False)
    prompt = (_PROMPT
              .replace("{language}", language or "ko")
              .replace("{persona}", persona)
              .replace("{items}", payload))
    try:
        data = QuizOutput.model_validate(invoke_json(get_worker_llm(), prompt))
    except Exception as exc:
        logger.warning("퀴즈 생성 실패, 미노출 처리: %s", type(exc).__name__)
        logger.debug("퀴즈 생성 실패 상세", exc_info=exc)
        return []

    passed = [q.model_dump() for q in data.questions if _grounded(q.model_dump(), sources)]
    dropped = len(data.questions) - len(passed)
    if dropped:
        logger.info("퀴즈 가드: %d문항 중 %d개 폐기 (근거 조각 미실존)", len(data.questions), dropped)
    if len(passed) < _MIN_QUESTIONS:
        logger.info("퀴즈 미노출: 가드 통과 %d문항 < %d", len(passed), _MIN_QUESTIONS)
        return []
    return passed
