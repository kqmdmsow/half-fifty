"""설명문 난이도 지표 (#174).

이 지표는 이해도를 재지 않는다 — 문장이 짧고 전문용어가 적으면 읽기 쉬울
개연성이 높다는 것뿐이다. 그 한계를 알고도 만드는 이유는, 사람 대상 조사
전까지 "고령층 모드는 쉬운 말로 설명한다"를 근거 없이 주장할 수 없기 때문이다.
"""

from src.readability import aggregate, jargon_hits, measure

HARD = ("임차인의 채무불이행이 있는 경우 임대인은 최고 없이 계약을 해지할 수 있으며, "
        "이때 발생하는 손해배상액의 예정으로서 보증금에서 이를 공제하고 잔액을 "
        "반환하되 그 이행지체에 따른 지체상금은 별도로 청구할 수 있다.")
EASY = ("돈을 제때 못 내면 집주인이 바로 계약을 끊을 수 있어요. "
        "그리고 보증금에서 위약금을 떼고 남은 돈만 돌려줘요. "
        "늦어진 기간만큼 돈을 더 물어낼 수도 있어요.")


def test_어려운_문장이_문장당_길이가_길다():
    assert measure(HARD)["avg_sentence_chars"] > measure(EASY)["avg_sentence_chars"]


def test_어려운_문장에_전문용어가_더_많다():
    assert measure(HARD)["jargon_count"] > measure(EASY)["jargon_count"]
    assert "채무불이행" in jargon_hits(HARD)


def test_쉬운_문장은_문장_수가_더_많다():
    # 같은 내용을 짧은 문장 여러 개로 쪼개는 것이 고령층 설명의 핵심이다.
    assert measure(EASY)["sentences"] > measure(HARD)["sentences"]


def test_읽기_시간은_글자수에_비례한다():
    m = measure("가" * 500)
    assert abs(m["read_seconds"] - 60) < 1


def test_소수점은_문장_경계가_아니다():
    # "1.5%"가 쪼개지면 문장 길이 지표가 왜곡된다.
    assert measure("중도상환수수료는 1.5%로 한다.")["sentences"] == 1


def test_빈_입력도_안전하게_처리한다():
    assert measure("")["chars"] == 0
    assert aggregate([])["chars"] == 0
    assert aggregate(["", "  "])["chars"] == 0


def test_집계는_평균을_낸다():
    agg = aggregate([HARD, EASY])
    assert measure(EASY)["chars"] < agg["chars"] < measure(HARD)["chars"]
