"""재생성 대상 분기(aspect별 라우팅) + 마진 규칙 테스트 (자문 §3, #75).

#35가 데모 재측정에서 실측으로 드러낸 구멍(clarity만 미달로 persona만
재실행하다 risk_coverage/faithfulness가 아슬아슬하게 통과한 오분류가 그대로
새어나감, FP 3→7)을 마진 규칙(shortcut_eligible)이 실제로 막는지 경계값
기준으로 검증한다.

Judge rationale을 재생성 프롬프트에 주입하는 부분(_feedback_block 등)은 이번
PR에서 제외했다 — 측정 결과 FP가 오히려 늘어(데모 contract_05 FP 1→5~6, 2회
일관) 별도 이슈에서 문구를 다시 설계하기로 했다. 이 파일은 라우팅/마진
로직만 검증한다.
"""
from src.graph import _route_retry_target
from src.state import JUDGE_THRESHOLD, RETRY_SHORTCUT_MARGIN, shortcut_eligible


def _scores(clarity=5, faith=5, cov=5, act=5, rationale=None):
    return {
        "clarity": clarity, "faithfulness": faith,
        "risk_coverage": cov, "actionability": act,
        "rationale": rationale or {},
    }


def _state(**kwargs):
    return {"judge_scores": _scores(**kwargs)}


MARGIN_FLOOR = JUDGE_THRESHOLD + RETRY_SHORTCUT_MARGIN  # 4.5 (기본값 기준)


def test_clarity_only_with_comfortable_margin_routes_to_persona():
    scores = _scores(clarity=2, faith=MARGIN_FLOOR, cov=MARGIN_FLOOR, act=5)
    assert shortcut_eligible(scores)
    assert _route_retry_target({"judge_scores": scores}) == "persona"


def test_clarity_only_but_borderline_risk_coverage_routes_to_analysis():
    # #35 실측 재현 조건: risk_coverage가 임계값(3.5)은 넘었지만 마진(4.5) 미달
    scores = _scores(clarity=2, faith=MARGIN_FLOOR, cov=MARGIN_FLOOR - 0.1, act=5)
    assert not shortcut_eligible(scores)
    assert _route_retry_target({"judge_scores": scores}) == "analysis"


def test_clarity_only_but_borderline_faithfulness_routes_to_analysis():
    scores = _scores(clarity=2, faith=MARGIN_FLOOR - 0.5, cov=MARGIN_FLOOR, act=5)
    assert not shortcut_eligible(scores)
    assert _route_retry_target({"judge_scores": scores}) == "analysis"


def test_clarity_plus_actionability_failing_routes_to_analysis():
    # persona는 check_questions을 재생성하지 않으므로 clarity 외 다른 aspect가
    # 같이 미달이면(=exact match 아님) 무조건 analysis
    scores = _scores(clarity=2, faith=5, cov=5, act=2)
    assert _route_retry_target({"judge_scores": scores}) == "analysis"


def test_faithfulness_only_routes_to_analysis():
    scores = _scores(clarity=5, faith=2, cov=5, act=5)
    assert _route_retry_target({"judge_scores": scores}) == "analysis"


def test_risk_coverage_only_routes_to_analysis():
    scores = _scores(clarity=5, faith=5, cov=2, act=5)
    assert _route_retry_target({"judge_scores": scores}) == "analysis"


def test_no_failing_aspects_defaults_to_analysis():
    # _route_after_judge가 이미 "pass"로 걸러내는 경우라 실제로는 호출 안 되지만,
    # 방어적으로 안전한 기본값(analysis)을 확인
    assert _route_retry_target(_state()) == "analysis"
