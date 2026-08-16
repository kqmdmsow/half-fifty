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
