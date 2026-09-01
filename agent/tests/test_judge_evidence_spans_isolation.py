"""evidence_spans·section이 비스트리밍(graph.py) 경로에서도 Judge 입력에
새어 들어가지 않는지 확인하는 회귀 테스트 (#192 후속).

스트리밍 경로는 stream.py의 이벤트 조립 단계에서 걸러지지만(#192,
test_case_footnotes_judge_isolation.py), graph.py 경로는 그런 별도 조립
단계가 없어 judge_node(judge.py) 자체에서 걸러야 한다. 이 테스트는 그
필터링이 실제 judge_node 함수(LLM 호출만 mock) 안에서 작동하는지 본다 —
judge_node를 통째로 fake로 바꾸는 격리 테스트로는 이 부분을 못 잡는다.
"""

from unittest.mock import patch

from src.nodes.judge import judge_node

_PASSING = {
    "clarity": {"score": 5, "rationale": "ok"},
    "faithfulness": {"score": 5, "rationale": "ok"},
    "risk_coverage": {"score": 5, "rationale": "ok"},
    "actionability": {"score": 5, "rationale": "ok"},
}


def _state_with_evidence_spans():
    return {
        "persona": "adult",
        "clauses": [{"clause_id": "clause_001", "text": "이 사건 주택에 관한 모든 수리비용은 임차인의 책임으로 한다."}],
        "adapted_results": [{
            "clause_id": "clause_001",
            "explanation": "수리비용을 임차인이 전부 부담해야 한다는 조항이에요.",
            "risk_level": "위험",
            "risk_type": "책임 면제",
            "risk_evidence": "이 사건 주택에 관한 모든 수리비용은 임차인의 책임으로 한다",
            "check_questions": ["임대인 유지수선의무를 확인해보세요."],
            # graph.py(analysis_node)가 _analyze_clause에서 그대로 받는 표시 전용 필드 —
            # locate_quotes가 실제로 채워 넣는 형태([[start, end], ...])
            "evidence_spans": [[5, 20]],
            "section": "본문",
        }],
    }


def test_evidence_spans가_judge_프롬프트에_안_실린다():
    captured_prompts = []

    def fake_invoke_json(llm, prompt):
        captured_prompts.append(prompt)
        return _PASSING

    with patch("src.nodes.judge.get_judge_llm", return_value=object()), \
         patch("src.nodes.judge.invoke_json", side_effect=fake_invoke_json):
        result = judge_node(_state_with_evidence_spans())

    assert result["judge_scores"]["clarity"] == 5.0
    assert captured_prompts, "invoke_json이 호출되지 않음"
    prompt = captured_prompts[0]
    assert "evidence_spans" not in prompt, "evidence_spans가 judge 프롬프트에 새어 들어감(비스트리밍 경로)"
    assert '"section"' not in prompt, "section이 judge 프롬프트에 새어 들어감(비스트리밍 경로)"
    # 판정에 필요한 정보는 그대로 살아있어야 한다(격리는 표시 필드만 빼는 것)
    assert "책임 면제" in prompt
    assert "이 사건 주택에 관한 모든 수리비용은 임차인의 책임으로 한다" in prompt
