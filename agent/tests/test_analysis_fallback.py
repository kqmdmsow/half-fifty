"""분석 폴백 마커 테스트 (#100) — 재시도 소진 시 analysis_failed=True가 붙고,
persona._adapt의 dict 복사를 거쳐도 살아남는지 확인한다 (프론트 현지화 근거)."""
from unittest.mock import patch

from src.nodes.analysis import _analyze_clause, _FALLBACK_EVIDENCE


def _always_fail(*args, **kwargs):
    raise ValueError("강제 파싱 실패")


def test_폴백에_analysis_failed_마커():
    with patch("src.nodes.analysis.invoke_json", _always_fail), \
         patch("src.nodes.analysis.get_worker_llm", lambda: None):
        result = _analyze_clause("clause_001", "제1조 테스트 조항")
    assert result["risk_evidence"] == _FALLBACK_EVIDENCE
    assert result.get("analysis_failed") is True


def test_정상_결과에는_마커_없음():
    ok = {"explanation": "설명", "risk_level": "안전", "risk_type": "해당 없음",
          "risk_evidence": "근거 없음", "check_questions": []}
    with patch("src.nodes.analysis.invoke_json", lambda *a, **k: ok), \
         patch("src.nodes.analysis.get_worker_llm", lambda: None):
        result = _analyze_clause("clause_001", "제1조 테스트 조항")
    assert "analysis_failed" not in result


def test_마커가_dict_복사를_통과():
    # persona._adapt는 dict(result)로 복사한다 — 마커가 이벤트 payload까지 전달되는 근거
    fallback = {"clause_id": "c1", "explanation": "e", "risk_level": "주의",
                "risk_type": "해당 없음", "risk_evidence": _FALLBACK_EVIDENCE,
                "check_questions": [], "analysis_failed": True}
    adapted = dict(fallback)
    adapted["explanation"] = "새 설명"
    assert adapted["analysis_failed"] is True
