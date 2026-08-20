"""퀴즈 생성 가드 테스트 (#92) — LLM은 전부 모킹, 코드 검증 로직만 확인."""

from unittest.mock import patch

from src.quiz import generate_quiz

_ITEM = {
    "clause_id": "clause_003",
    "explanation": "신탁회사가 보증금 반환 책임을 지지 않는다는 조항이에요. 세입자가 보증금을 돌려받을 곳이 사라질 수 있어요.",
    "risk_level": "위험",
    "risk_type": "책임 면제",
    "risk_evidence": "조항에서 수탁자가 임대차보증금 반환책임이 없다고 명시하고 있습니다.",
}


def _q(quote, clause_id="clause_003"):
    return {"clause_id": clause_id, "question": "보증금 반환 책임은 누구에게 있나요?",
            "choices": ["신탁회사", "아무도 책임지지 않을 수 있음", "은행"],
            "answer_index": 1, "answer_quote": quote}


def _run(questions):
    with patch("src.quiz.invoke_json", return_value={"questions": questions}), \
         patch("src.quiz.get_worker_llm", lambda: None):
        return generate_quiz([_ITEM], "adult", "ko")


def test_근거_실존_문항은_통과():
    out = _run([_q("보증금을 돌려받을 곳이 사라질 수 있어요"),
                _q("수탁자가 임대차보증금 반환책임이 없다고 명시"),
                _q("신탁회사가 보증금 반환 책임을 지지 않는다")])
    assert len(out) == 3


def test_창작_근거_문항은_폐기():
    out = _run([_q("보증금을 돌려받을 곳이 사라질 수 있어요"),
                _q("수탁자가 임대차보증금 반환책임이 없다고 명시"),
                _q("법원 판례에 따르면 세입자가 반드시 승소합니다")])  # 창작
    assert len(out) == 2


def test_통과_2개_미만이면_전체_미노출():
    out = _run([_q("보증금을 돌려받을 곳이 사라질 수 있어요"),
                _q("이 근거는 어디에도 없습니다 정말로요"),
                _q("이것도 창작된 근거 조각입니다 확실히")])
    assert out == []


def test_모르는_clause_id는_폐기():
    out = _run([_q("보증금을 돌려받을 곳이 사라질 수 있어요"),
                _q("보증금을 돌려받을 곳이 사라질 수 있어요", clause_id="clause_999"),
                _q("수탁자가 임대차보증금 반환책임이 없다고 명시")])
    assert len(out) == 2


def test_짧은_근거는_폐기():
    out = _run([_q("보증금을 돌려받을 곳이 사라질 수 있어요"),
                _q("신탁회사"),  # 정규화 후 10자 미만
                _q("수탁자가 임대차보증금 반환책임이 없다고 명시")])
    assert len(out) == 2


def test_LLM_실패시_빈_목록():
    with patch("src.quiz.invoke_json", side_effect=ValueError("boom")), \
         patch("src.quiz.get_worker_llm", lambda: None):
        assert generate_quiz([_ITEM], "adult", "ko") == []


def test_빈_입력은_빈_목록():
    assert generate_quiz([], "adult", "ko") == []
