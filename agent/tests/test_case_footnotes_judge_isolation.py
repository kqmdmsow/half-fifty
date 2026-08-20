"""#91 격리 원칙 회귀 테스트: related_cases가 Judge 입력에 새어 들어가지 않는지
API 호출 없이 확인한다 (LLM은 전부 monkeypatch로 대체).

judge_node에 실제로 넘어가는 judge_state["adapted_results"]를 스파이로
가로채, 화면 표시용 related_cases 키가 거기 없는지 검증한다 — 있으면
Judge가 그 텍스트를 채점 근거로 잘못 읽을 위험(채점 오염, #91 최우선 설계
항목)이 현실화된 것이므로 이 테스트가 즉시 실패해야 한다.
"""

from unittest.mock import patch

from src.case_footnotes import get_related_cases
from src.state import Clause
from src.stream import stream_analysis

_CLAUSE = Clause(clause_id="clause_001", text="이 사건 주택에 관한 모든 수리비용은 임차인의 책임으로 한다.")

_FAKE_ANALYSIS_RESULT = {
    "clause_id": "clause_001",
    "explanation": "수리비용을 임차인이 전부 부담해야 한다는 조항이에요.",
    "risk_level": "위험",
    "risk_type": "책임 면제",  # case_footnotes.json에 각주가 있는 유형 — 누출되면 바로 드러남
    "risk_evidence": "이 사건 주택에 관한 모든 수리비용은 임차인의 책임으로 한다",
    "check_questions": ["임대인 유지수선의무를 확인해보세요."],
}

_PASSING_SCORES = {
    "clarity": 5.0, "faithfulness": 5.0, "risk_coverage": 5.0, "actionability": 5.0,
    "rationale": {},
}


def test_related_cases는_judge_입력에_섞이지_않음():
    assert get_related_cases("책임 면제"), "테스트 전제 실패 — 이 유형엔 각주가 있어야 함"

    captured_judge_states = []

    def fake_judge_node(state):
        captured_judge_states.append(state)
        return {"judge_scores": _PASSING_SCORES}

    with patch("src.stream.split_clauses_with_warnings", return_value=([_CLAUSE], [])), \
         patch("src.stream._analyze_clause", return_value=dict(_FAKE_ANALYSIS_RESULT)), \
         patch("src.stream.judge_node", side_effect=fake_judge_node):
        events = list(stream_analysis("이 사건 주택에 관한 모든 수리비용은 임차인의 책임으로 한다.", "adult"))

    # 1) 이벤트 payload에는 related_cases가 사용자 표시용으로 정상 포함돼야 한다.
    clause_events = [e for e in events if e["event"] == "clause"]
    assert clause_events, "clause 이벤트가 안 나옴"
    assert clause_events[-1]["result"]["related_cases"] == get_related_cases("책임 면제")

    # 2) 그러나 judge_node가 실제로 받은 state에는 related_cases가 전혀 없어야 한다 —
    #    있으면 Judge가 채점 근거로 잘못 읽을 위험(채점 오염).
    assert captured_judge_states, "judge_node가 호출되지 않음"
    for state in captured_judge_states:
        for r in state["adapted_results"]:
            assert "related_cases" not in r, "related_cases가 Judge 입력에 새어 들어감 — 격리 원칙 위반"
