"""공식 평가 하네스의 반복 다수결·폴백 감지·원자료 저장 검증 (#161, #163 후속).

API 호출 없이 `_analyze_clause`를 모킹해 하네스 로직만 본다.
"""

import importlib
import json
import sys
from pathlib import Path

import pytest


def _load(monkeypatch, argv, side_effect):
    """eval_real_labels를 주어진 argv로 재임포트하고 _analyze_clause를 모킹한다."""
    monkeypatch.setattr(sys, "argv", ["eval_real_labels.py", *argv])
    sys.modules.pop("eval_real_labels", None)
    mod = importlib.import_module("eval_real_labels")
    monkeypatch.setattr(mod, "_analyze_clause", side_effect)
    return mod


def _pred(level, evidence="원문 인용"):
    return {"clause_id": "c", "explanation": "e", "risk_level": level,
            "risk_type": "해당 없음", "risk_evidence": evidence, "check_questions": []}


def _fallback_pred():
    from src.nodes.analysis import _FALLBACK_EVIDENCE
    return _pred("주의", _FALLBACK_EVIDENCE)


def _row(case_id="x", split="test"):
    return {"case_id": case_id, "split": split, "clause_text": "t",
            "gold_risk_level": "위험", "gold_risk_type": "책임 면제", "label_grade": "A"}


def test_majority_vote_resolves_flapping(monkeypatch):
    # 같은 조항이 회차마다 흔들려도 다수결로 확정된다
    seq = iter([_pred("위험"), _pred("안전"), _pred("위험")] * 100)
    mod = _load(monkeypatch, ["out.md", "train"], lambda cid, text: next(seq))
    monkeypatch.setattr(mod, "_load_labels", lambda: [_row(split="train")])

    results = mod.run_eval(repeats=3)
    assert results[0]["prediction"]["risk_level"] == "위험"
    assert results[0]["tie"] is False
    assert len(results[0]["runs"]) == 3


def test_tie_is_flagged(monkeypatch):
    # 과반이 없으면 tie로 표시해 별도 집계할 수 있어야 한다
    seq = iter([_pred("위험"), _pred("안전")] * 100)
    mod = _load(monkeypatch, ["out.md"], lambda cid, text: next(seq))
    monkeypatch.setattr(mod, "_load_labels", lambda: [_row()])

    results = mod.run_eval(repeats=2)
    assert results[0]["tie"] is True


def test_isolated_full_fallback_does_not_abort(monkeypatch):
    # real_003_24 사례: 조항 하나가 재시도(citation_check 등) 소진으로 전체
    # 폴백해도, 그 자체로는 배치를 중단하지 않고 정확도 집계에서만 제외한다.
    rows = [_row("a"), _row("b"), _row("c")]
    # a는 전체 폴백, b·c는 정상 — 연속 3개가 아니라 1개만 폴백이라 안전.
    seq = iter([_fallback_pred(), _fallback_pred(), _fallback_pred()]
               + [_pred("위험")] * 100)
    mod = _load(monkeypatch, ["out.md"], lambda cid, text: next(seq))
    monkeypatch.setattr(mod, "_load_labels", lambda: rows)

    results = mod.run_eval(repeats=3)
    assert len(results) == 3
    assert results[0]["fully_fallback"] is True
    assert results[0]["prediction"] is None
    assert results[0]["fallback_count"] == 3
    assert results[1]["fully_fallback"] is False
    assert results[2]["fully_fallback"] is False


def test_partial_fallback_excludes_fallback_runs_from_majority(monkeypatch):
    # 3회 중 1회만 폴백이면, 폴백 회차는 다수결에서 제외하고 남은 유효 회차로
    # 확정한다 — 폴백이 판정 결과를 오염시키지 않아야 한다.
    seq = iter([_pred("위험"), _fallback_pred(), _pred("위험")] * 100)
    mod = _load(monkeypatch, ["out.md"], lambda cid, text: next(seq))
    monkeypatch.setattr(mod, "_load_labels", lambda: [_row()])

    results = mod.run_eval(repeats=3)
    assert results[0]["fully_fallback"] is False
    assert results[0]["fallback_count"] == 1
    assert results[0]["prediction"]["risk_level"] == "위험"
    assert len(results[0]["runs"]) == 2  # 폴백 1회 제외한 유효 회차만


def test_consecutive_full_fallback_triggers_systemic_failure(monkeypatch):
    # 연속으로 여러 조항이 통째 폴백하면 API 이상(크레딧 소진 등)으로 보고 중단
    rows = [_row("a"), _row("b"), _row("c"), _row("d")]
    mod = _load(monkeypatch, ["out.md"], lambda cid, text: _fallback_pred())
    monkeypatch.setattr(mod, "_load_labels", lambda: rows)

    with pytest.raises(mod.SystemicFailureDetected):
        mod.run_eval(repeats=2)


def test_raw_dump_keeps_every_run(monkeypatch, tmp_path):
    # 수치가 움직였을 때 재실행 없이 대조하려면 회차별 예측이 남아야 한다
    seq = iter([_pred("위험"), _pred("안전"), _pred("위험")] * 100)
    mod = _load(monkeypatch, ["out.md"], lambda cid, text: next(seq))
    monkeypatch.setattr(mod, "_load_labels", lambda: [_row()])

    results = mod.run_eval(repeats=3)
    out = tmp_path / "raw.json"
    mod._dump_raw(results, out, 3)

    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["repeats"] == 3
    assert [a["risk_level"] for a in saved["items"][0]["attempts"]] == ["위험", "안전", "위험"]
    assert saved["items"][0]["final_risk_level"] == "위험"
    assert saved["items"][0]["fallback_count"] == 0
    assert saved["items"][0]["fully_fallback"] is False


def test_raw_dump_records_fully_fallback_clause(monkeypatch, tmp_path):
    # 전체 폴백 조항도 원자료에는 남아야 한다 (final_risk_level=None으로 명시)
    seq = iter([_fallback_pred(), _fallback_pred()] + [_pred("위험")] * 100)
    mod = _load(monkeypatch, ["out.md"], lambda cid, text: next(seq))
    monkeypatch.setattr(mod, "_load_labels", lambda: [_row("a"), _row("b")])

    results = mod.run_eval(repeats=2)
    out = tmp_path / "raw.json"
    mod._dump_raw(results, out, 2)

    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["items"][0]["fully_fallback"] is True
    assert saved["items"][0]["final_risk_level"] is None
    assert saved["items"][0]["fallback_count"] == 2
