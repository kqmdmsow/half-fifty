"""인용 원문 존재 검사 테스트."""
from unittest.mock import patch

from src.citation_check import extract_quotes, find_fabricated_quotes

CLAUSE = "임차인이 차임을 2기 이상 연체한 때에는 임대인은 본 계약을 해지할 수 있다."


def test_existing_quote_passes():
    ev = '조항의 "2기 이상 연체한 때"라는 표현이 근거입니다.'
    assert find_fabricated_quotes(ev, CLAUSE) == []


def test_fabricated_quote_detected():
    ev = '조항의 "즉시 명도를 청구할 수 있다"라는 표현이 근거입니다.'
    assert len(find_fabricated_quotes(ev, CLAUSE)) == 1


def test_whitespace_and_quote_style_ignored():
    ev = "「2기 이상  연체한때」 부분이 문제입니다."
    assert find_fabricated_quotes(ev, CLAUSE) == []


def test_paraphrase_without_quotes_not_checked():
    ev = "차임을 두 번 밀리면 계약이 해지될 수 있다는 내용입니다."
    assert find_fabricated_quotes(ev, CLAUSE) == []


def test_short_quotes_skipped():
    ev = '"2기"라는 표현.'  # 5자 미만 — 검사 대상 아님
    assert extract_quotes(ev) == []


def test_ellipsis_split_segments_checked():
    ev = '"차임을 2기 이상 … 해지할 수 있다"는 조항.'
    assert find_fabricated_quotes(ev, CLAUSE) == []


def test_가운뎃점_유니코드_변형은_오탐_아님():
    """모델이 ·(U+00B7)를 ・(U+30FB)로 바꿔 써도 같은 인용으로 인정 — val clause_020 실측 사례."""
    clause = "명의인·계좌번호·비밀번호가 맞으면 그 요청자를 본인으로 본다."
    evidence = "「명의인・계좌번호・비밀번호가 맞으면 그 요청자를 본인으로」라고 명시되어 있다."
    assert find_fabricated_quotes(evidence, clause) == []


def test_대시_변형도_동일_인용_인정():
    clause = "보증금 반환은 계약 종료 후-즉시-이행한다."
    evidence = "원문은 「보증금 반환은 계약 종료 후—즉시—이행한다」고 정한다."
    assert find_fabricated_quotes(evidence, clause) == []


def test_법령_출처_명시_인용은_면제():
    """법령 문구 인용(출처 명시)은 원문 인용이 아님 — #49 도메인 주입 후 실측 오판 사례."""
    clause = "임차인이 2기의 차임액에 달하도록 연체한 때에는 임대인은 계약을 해지할 수 있다."
    evidence = ("상가건물임대차보호법 제10조는 '3기의 차임액에 달하도록 차임을 연체한 때'를 "
                "강행 기준으로 규정하고 있어, 본 조항의 2기 기준은 법정 보호를 축소합니다.")
    assert find_fabricated_quotes(evidence, clause) == []


def test_출처_없는_창작_인용은_여전히_적발():
    clause = "임차인이 2기의 차임액에 달하도록 연체한 때에는 임대인은 계약을 해지할 수 있다."
    evidence = "조항에서 '보증금은 반환하지 아니한다'라고 명시하고 있습니다."
    assert find_fabricated_quotes(evidence, clause) == ["보증금은 반환하지 아니한다"]


def test_법령_표지가_멀면_면제_안됨():
    clause = "임차인은 보증금을 지급한다."
    evidence = ("민법 제640조와 관련하여 여러 판례가 있습니다. 그리고 완전히 별개의 맥락에서 "
                "이 조항은 임차인에게 매우 불리한 구조입니다. 원문은 '임대인은 언제든 해지할 수 있다'입니다.")
    assert find_fabricated_quotes(evidence, clause) == ["임대인은 언제든 해지할 수 있다"]


# 검사 대상을 조항 원문(text)이 아니라 프롬프트 전체(prefix+text+suffix)로 넓히면,
# 모델이 analysis.txt 안의 예시 문구를 조항과 무관하게 risk_evidence에 그대로
# 베껴도 "입력에 있으니 통과"로 새어나간다 — 2026-08 PR#50 리뷰 중 실측된 회귀.
# 이 테스트는 그 구멍이 다시 열리면 API 호출 없이 바로 잡는다.
def test_프롬프트_예시_문구_재도용은_적발된다():
    from src.nodes import analysis as analysis_module

    unrelated_clause = {
        "clause_id": "clause_999",
        "text": "제7조 임대인은 필요하다고 판단되는 경우 언제든지 계약을 해지할 수 있다.",
    }
    # analysis.txt에 실제로 존재하는 예시 문구여야 이 테스트가 의미가 있다.
    prompt_example_phrases = [
        "시장 여건을 감안하여 조정할 수 있다",
        "상환원금의 1.5% 중도상환수수료",
        "별도 약정이 없는 한 계약금을 손해배상의 기준으로 본다",
    ]
    for phrase in prompt_example_phrases:
        assert phrase in analysis_module._PROMPT_PREFIX

    for phrase in prompt_example_phrases:
        fake_response = {
            "explanation": "설명",
            "risk_level": "위험",
            "risk_type": "일방적 계약 해지",
            "risk_evidence": f'조항 근거: "{phrase}"',
            "check_questions": [],
        }
        with patch.object(analysis_module, "invoke_json", return_value=fake_response):
            result = analysis_module._analyze_clause(
                unrelated_clause["clause_id"], unrelated_clause["text"])
        # 조항과 무관한 프롬프트 예시를 인용했으므로 창작 인용으로 잡혀
        # 재시도 소진 후 폴백(분석 실패)으로 떨어져야 한다.
        assert result["risk_evidence"] == analysis_module._FALLBACK_EVIDENCE, (
            f"'{phrase}' 재도용이 적발되지 않음 — 검사 범위가 다시 넓어졌을 가능성")
