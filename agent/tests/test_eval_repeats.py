"""공식 평가 하네스의 반복 다수결·폴백 감지·원자료 저장 검증 (#161).

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


def test_majority_vote_resolves_flapping(monkeypatch):
    # 같은 조항이 회차마다 흔들려도 다수결로 확정된다
    seq = iter([_pred("위험"), _pred("안전"), _pred("위험")] * 100)
    mod = _load(monkeypatch, ["out.md", "train"], lambda cid, text: next(seq))
    monkeypatch.setattr(mod, "_load_labels", lambda: [
        {"case_id": "x", "split": "train", "clause_text": "t",
         "gold_risk_level": "위험", "gold_risk_type": "책임 면제", "label_grade": "A"}])

    results = mod.run_eval(repeats=3)
    assert results[0]["prediction"]["risk_level"] == "위험"
    assert results[0]["tie"] is False
    assert len(results[0]["runs"]) == 3


def test_tie_is_flagged(monkeypatch):
    # 과반이 없으면 tie로 표시해 별도 집계할 수 있어야 한다
    seq = iter([_pred("위험"), _pred("안전")] * 100)
    mod = _load(monkeypatch, ["out.md"], lambda cid, text: next(seq))
    monkeypatch.setattr(mod, "_load_labels", lambda: [
        {"case_id": "x", "split": "test", "clause_text": "t",
         "gold_risk_level": "위험", "gold_risk_type": "책임 면제", "label_grade": "A"}])

    results = mod.run_eval(repeats=2)
    assert results[0]["tie"] is True


def test_fallback_aborts_the_run(monkeypatch):
    # 폴백은 데이터가 아니라 사고다 — 조용히 집계되면 안 된다 (2026-08-07 사고)
    from src.nodes.analysis import _FALLBACK_EVIDENCE

    mod = _load(monkeypatch, ["out.md"],
                lambda cid, text: _pred("주의", _FALLBACK_EVIDENCE))
    monkeypatch.setattr(mod, "_load_labels", lambda: [
        {"case_id": "x", "split": "test", "clause_text": "t",
         "gold_risk_level": "위험", "gold_risk_type": "책임 면제", "label_grade": "A"}])

    with pytest.raises(mod.FallbackDetected):
        mod.run_eval(repeats=1)


def test_raw_dump_keeps_every_run(monkeypatch, tmp_path):
    # 수치가 움직였을 때 재실행 없이 대조하려면 회차별 예측이 남아야 한다
    seq = iter([_pred("위험"), _pred("안전"), _pred("위험")] * 100)
    mod = _load(monkeypatch, ["out.md"], lambda cid, text: next(seq))
    monkeypatch.setattr(mod, "_load_labels", lambda: [
        {"case_id": "x", "split": "test", "clause_text": "t",
         "gold_risk_level": "위험", "gold_risk_type": "책임 면제", "label_grade": "A"}])

    results = mod.run_eval(repeats=3)
    out = tmp_path / "raw.json"
    mod._dump_raw(results, out, 3)

    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["repeats"] == 3
    assert [r["risk_level"] for r in saved["items"][0]["runs"]] == ["위험", "안전", "위험"]
    assert saved["items"][0]["final_risk_level"] == "위험"
