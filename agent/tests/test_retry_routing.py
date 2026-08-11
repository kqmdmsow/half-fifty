"""재생성 조건 분기 테스트 (자문 §3)."""
from src.graph import _failing_aspects, _format_feedback, _route_retry_target


def _scores(clarity=5.0, faith=5.0, cov=5.0, act=5.0):
    return {"clarity": clarity, "faithfulness": faith, "risk_coverage": cov,
            "actionability": act,
            "rationale": {"clarity": "용어가 어려움", "faithfulness": "근거 창작"}}


def test_clarity_only_routes_to_persona():
    s = {"judge_scores": _scores(clarity=2.0)}
    assert _route_retry_target(s) == "persona"


def test_faithfulness_low_routes_to_analysis():
    s = {"judge_scores": _scores(clarity=2.0, faith=2.0)}
    assert _route_retry_target(s) == "analysis"


def test_coverage_low_routes_to_analysis():
    s = {"judge_scores": _scores(cov=3.0)}
    assert _route_retry_target(s) == "analysis"


def test_no_failing_defaults_to_analysis():
    # 경계 케이스(전 aspect 통과인데 재시도 진입)는 안전하게 전체 재실행
    assert _route_retry_target({"judge_scores": _scores()}) == "analysis"


def test_feedback_contains_failing_aspects_only():
    fb = _format_feedback(_scores(clarity=2.0))
    assert "clarity" in fb and "용어가 어려움" in fb
    assert "faithfulness" not in fb


def test_failing_aspects_threshold():
    assert _failing_aspects(_scores(faith=3.0, act=3.4)) == ["faithfulness", "actionability"]
