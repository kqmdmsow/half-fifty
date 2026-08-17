"""인용 원문 존재 검사 테스트."""
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
