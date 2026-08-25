"""REST 응답이 방화벽 상태를 빠뜨리지 않는지 (#174).

스트리밍 경로(/analyze-stream)는 dict를 그대로 흘리지만 REST 경로
(/analyze·/analyze-pdf·/analyze-image)는 Pydantic 스키마와 백엔드 record DTO를
거친다. 둘 중 어디든 필드가 빠지면 **같은 서비스가 호출 경로에 따라 다른
정보를 준다.** 실제로 analysis_failed가 그렇게 조용히 사라지고 있었다.

방화벽 상태(injection_suspected·quarantined·verdict_withheld)는 유실되면
사용자가 방어 동작을 볼 수 없고 감사도 불가능하므로 회귀를 고정한다.
"""

import main as agent_main


def _state(result_overrides: dict) -> dict:
    base = {
        "clause_id": "clause_001", "explanation": "설명", "risk_level": "주의",
        "risk_type": "문서 조작 의심", "risk_evidence": "근거",
        "check_questions": ["질문"],
    }
    base.update(result_overrides)
    return {
        "clauses": [{"clause_id": "clause_001", "text": "제1조 원문"}],
        "adapted_results": [base],
        "translations": {},
        "judge_scores": {"clarity": 4.0, "faithfulness": 4.0,
                         "risk_coverage": 4.0, "actionability": 4.0},
        "retry_count": 0, "needs_review": False, "parse_warnings": [],
    }


def test_방화벽_상태가_REST_응답에_실린다():
    res = agent_main._state_to_response(_state({
        "injection_suspected": True, "quarantined": 2,
        "verdict_withheld": True, "original_risk_level": "안전",
    }))
    c = res.results[0]
    assert c.injection_suspected is True
    assert c.quarantined == 2
    assert c.verdict_withheld is True
    assert c.original_risk_level == "안전"


def test_분석_실패_마커가_REST_응답에_실린다():
    res = agent_main._state_to_response(_state({"analysis_failed": True}))
    assert res.results[0].analysis_failed is True


def test_평상시에는_전부_기본값():
    # 정상 조항에 방화벽 플래그가 붙으면 화면에 헛경고가 뜬다.
    res = agent_main._state_to_response(_state({"risk_level": "안전"}))
    c = res.results[0]
    assert (c.injection_suspected, c.quarantined, c.verdict_withheld,
            c.original_risk_level, c.analysis_failed) == (False, 0, False, None, False)


def test_경고_코드가_REST_응답에_실린다():
    # 프론트가 16개 언어로 현지화하는 근거. 빠지면 한국어 원문으로 떨어진다.
    st = _state({})
    st["parse_warnings"] = ["🚫 이 조항에서 AI에게 내리는 지시로 보이는 문장 1건을 격리했습니다."]
    res = agent_main._state_to_response(st)
    assert res.parse_warning_codes == ["clause_quarantined"]
