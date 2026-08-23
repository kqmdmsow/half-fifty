"""평가 공통 모듈(RepeatRunner)의 반복 다수결·폴백 판정 검증 (#161).

API 호출 없이 콜러블을 주입해 하네스 로직만 본다.
"""

import pytest

from src.eval_repeat import (
    CONSECUTIVE_FULL_FALLBACK_LIMIT,
    RepeatRunner,
    SystemicFailureDetected,
    is_fallback,
    majority,
)
from src.nodes.analysis import _FALLBACK_EVIDENCE


def _pred(level, evidence="원문 인용"):
    return {"clause_id": "c", "explanation": "e", "risk_level": level,
            "risk_type": "해당 없음", "risk_evidence": evidence, "check_questions": []}


def _fallback():
    return _pred("주의", _FALLBACK_EVIDENCE)


def test_majority_resolves_flapping():
    assert majority(["위험", "안전", "위험"]) == ("위험", False)


def test_majority_flags_tie():
    _, tie = majority(["위험", "안전"])
    assert tie is True


def test_is_fallback_detects_only_fallback_evidence():
    assert is_fallback(_fallback()) is True
    assert is_fallback(_pred("주의")) is False


def test_runner_majority_and_representative_prediction():
    seq = iter([_pred("위험"), _pred("안전"), _pred("위험")])
    out = RepeatRunner(repeats=3).run(lambda: next(seq), label="x")
    assert out.prediction["risk_level"] == "위험"
    assert out.tie is False
    assert out.fully_fallback is False
    assert len(out.runs) == 3


def test_runner_excludes_fallback_rounds_from_vote():
    # 폴백 회차는 표에서 빠진다 — 남은 2회가 '안전'이면 확정도 '안전'
    seq = iter([_fallback(), _pred("안전"), _pred("안전")])
    out = RepeatRunner(repeats=3).run(lambda: next(seq), label="x")
    assert out.prediction["risk_level"] == "안전"
    assert out.fallback_count == 1
    assert len(out.runs) == 2


def test_runner_marks_fully_fallback_without_aborting():
    # 한 항목이 통째로 폴백해도 그 자체로는 중단하지 않는다 (#165)
    runner = RepeatRunner(repeats=2)
    out = runner.run(lambda: _fallback(), label="x")
    assert out.fully_fallback is True
    assert out.prediction is None
    assert runner.fully_fallback_labels == ["x"]


def test_runner_aborts_on_consecutive_full_fallback():
    # 연속 전체 폴백은 API 이상 신호 — 2026-08-07 오염 사고의 재발 방지
    runner = RepeatRunner(repeats=1)
    with pytest.raises(SystemicFailureDetected):
        for i in range(CONSECUTIVE_FULL_FALLBACK_LIMIT):
            runner.run(lambda: _fallback(), label=f"c{i}")


def test_valid_response_resets_consecutive_counter():
    # 중간에 유효 응답이 나오면 연속 카운터가 리셋돼 중단되지 않는다
    runner = RepeatRunner(repeats=1)
    runner.run(lambda: _fallback(), label="a")
    runner.run(lambda: _fallback(), label="b")
    runner.run(lambda: _pred("안전"), label="c")
    runner.run(lambda: _fallback(), label="d")
    runner.run(lambda: _fallback(), label="e")
    assert len(runner.fully_fallback_labels) == 4


def test_summary_reports_fallback_and_tie_counts():
    runner = RepeatRunner(repeats=2)
    seq = iter([_pred("위험"), _pred("안전")])
    runner.run(lambda: next(seq), label="tie-case")
    s = runner.summary()
    assert "2회" in s and "과반 없음 1건" in s


def test_repeats_must_be_positive():
    with pytest.raises(ValueError):
        RepeatRunner(repeats=0)
