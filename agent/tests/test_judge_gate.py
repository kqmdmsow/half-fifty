"""Judge 게이트 라우팅 테스트 — faithfulness 필수 조건 (자문 §5)."""
from src.graph import _route_after_judge


def _state(clarity=5, faith=5, cov=5, act=5, retry=0):
    return {"judge_scores": {"clarity": clarity, "faithfulness": faith,
                             "risk_coverage": cov, "actionability": act,
                             "rationale": {}},
            "retry_count": retry}


def test_high_avg_passes():
    assert _route_after_judge(_state()) == "pass"


def test_low_faithfulness_fails_despite_high_avg():
    # 평균 4.25 >= 3.5지만 faithfulness 2점 → 평균 무관 재시도
    assert _route_after_judge(_state(clarity=5, faith=2, cov=5, act=5)) == "retry"


def test_low_faithfulness_exhausted_flags():
    assert _route_after_judge(_state(faith=2, retry=2)) == "flag"


def test_low_avg_still_retries():
    assert _route_after_judge(_state(clarity=2, faith=4, cov=2, act=2)) == "retry"


def test_boundary_faithfulness_passes():
    assert _route_after_judge(_state(faith=3)) == "pass"
