"""재설명 judge 게이트 테스트 (#76) — LLM·judge 전부 모킹."""

from unittest.mock import patch

from src.reexplain import reexplain

_ANALYSIS = {
    "explanation": "신탁회사가 보증금 반환 책임을 지지 않는 위험한 조항이에요.",
    "risk_level": "위험",
    "risk_type": "책임 면제",
    "risk_evidence": "수탁자가 반환책임이 없다고 명시합니다.",
    "check_questions": ["책임 주체를 확인하세요."],
}
_CLAUSE = "제3조(특약) 수탁자는 임대차보증금 반환책임이 없다."

_PASS = {"clarity": 5.0, "faithfulness": 5.0, "risk_coverage": 4.5,
         "actionability": 4.5, "rationale": {}}
_FAIL_FAITH = {"clarity": 5.0, "faithfulness": 2.0, "risk_coverage": 5.0,
               "actionability": 5.0, "rationale": {}}


def _run(gen_returns, judge_returns):
    gen_iter = iter(gen_returns)
    judge_iter = iter(judge_returns)
    with patch("src.reexplain.invoke_json", side_effect=lambda *a, **k: next(gen_iter)), \
         patch("src.reexplain.get_worker_llm", lambda: None), \
         patch("src.reexplain.judge_node", side_effect=lambda s: {"judge_scores": next(judge_iter)}):
        return reexplain("clause_003", _CLAUSE, dict(_ANALYSIS), "easier")


def test_게이트_통과시_새_설명_반환():
    out = _run([{"explanation": "쉽게 말하면, 보증금을 돌려줄 회사가 책임을 안 진다는 뜻이에요."}], [_PASS])
    assert out["ok"] is True
    assert "쉽게 말하면" in out["explanation"]
    assert out["judge_scores"]["faithfulness"] == 5.0


def test_faithfulness_미달시_1회_재생성_후_통과():
    out = _run(
        [{"explanation": "첫 시도 설명입니다. 근거가 좀 흔들리는 버전이에요."},
         {"explanation": "두 번째 시도 설명입니다. 원문에 충실한 버전이에요."}],
        [_FAIL_FAITH, _PASS])
    assert out["ok"] is True and out["retry_count"] == 1
    assert "두 번째" in out["explanation"]


def test_재시도_소진시_ok_False_기존설명_유지_신호():
    out = _run(
        [{"explanation": "미달 설명 1입니다. 길이는 충분합니다."},
         {"explanation": "미달 설명 2입니다. 길이는 충분합니다."}],
        [_FAIL_FAITH, _FAIL_FAITH])
    assert out["ok"] is False and out["reason"] == "gate_failed"


def test_판정_필드는_반환에_없음_판정불변():
    out = _run([{"explanation": "쉽게 말하면, 보증금 책임 주체가 사라질 수 있다는 뜻이에요."}], [_PASS])
    assert "risk_level" not in out  # explanation만 반환 — 판정은 프론트가 기존 값 유지


def test_알수없는_mode는_거부():
    out = reexplain("c1", _CLAUSE, dict(_ANALYSIS), "banana")
    assert out["ok"] is False and out["reason"] == "unknown_mode"


def test_짧은_설명은_생성실패로_처리():
    out = _run([{"explanation": "짧다"}, {"explanation": "이건 충분히 긴 두 번째 설명이에요. 원문에 충실합니다."}],
               [_PASS])
    assert out["ok"] is True and out["retry_count"] == 1
