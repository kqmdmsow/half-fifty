"""판정 근거의 원문 위치 (#174).

사용자가 판정을 검증하려면 근거가 원문 어느 대목인지 눈으로 짚을 수 있어야
한다. 위치를 프론트에서 문자열 검색으로 다시 찾으면 공백·표기 차이로 어긋나고,
무엇보다 "근거가 원문에 실재하는가"를 두 곳에서 다르게 판단하게 된다.
"""

from src.citation_check import locate_quotes

CLAUSE = ("제3조(기한의 이익 상실) 을이 이자 지급을 1회라도 지체한 경우 "
          "갑은 즉시 대출금 전액의 상환을 청구할 수 있다.")


def test_인용_구간을_원문에서_찾는다():
    spans = locate_quotes("조항이 「이자 지급을 1회라도 지체한 경우」라고 정한다.", CLAUSE)
    assert len(spans) == 1
    start, end = spans[0]
    assert CLAUSE[start:end] == "이자 지급을 1회라도 지체한 경우"


def test_인용에_개행이_끼어도_원문_위치를_찾는다():
    # PDF 추출 텍스트는 단어 중간에 개행·공백이 들어가는 일이 흔하다.
    spans = locate_quotes("「즉시 대출금 전액의\n상환을 청구할 수 있다」가 문제다.", CLAUSE)
    assert len(spans) == 1
    assert "상환을 청구할 수 있다" in CLAUSE[spans[0][0]:spans[0][1]]


def test_원문에_없는_인용은_위치를_내지_않는다():
    # 창작 인용은 find_fabricated_quotes가 따로 걸러 재시도시킨다.
    assert locate_quotes("「존재하지 않는 문구입니다」", CLAUSE) == []


def test_겹치는_구간은_병합한다():
    # 하이라이트가 중첩되면 화면에서 깨진다.
    ev = "「이자 지급을 1회라도」와 「1회라도 지체한 경우」"
    spans = locate_quotes(ev, CLAUSE)
    assert len(spans) == 1


def test_구간은_정렬돼_나온다():
    ev = "「상환을 청구할 수 있다」와 「이자 지급을 1회라도」"
    spans = locate_quotes(ev, CLAUSE)
    assert spans == sorted(spans)


def test_너무_짧은_인용은_무시한다():
    # 두세 글자 인용을 하이라이트하면 원문 곳곳이 무의미하게 칠해진다.
    assert locate_quotes("「이자」", CLAUSE) == []
