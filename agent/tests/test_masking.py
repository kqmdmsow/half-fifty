"""개인정보 마스킹 테스트.

핵심 검증 축 두 개:
1. 가려야 할 것(주민번호·전화·이메일·카드·키워드 앵커 계좌)을 가리는가
2. 가리면 안 되는 것(금액·날짜·조항 번호·연체 기수)을 건드리지 않는가 —
   위험 판정 근거 숫자가 망가지면 마스킹이 분석 자체를 훼손한다.
"""

from src.masking import mask_pii, masking_notice


def test_주민등록번호_마스킹():
    text = "임차인 홍길동 (주민등록번호 900101-1234567)"
    masked, counts = mask_pii(text)
    assert "[주민등록번호]" in masked
    assert "900101" not in masked
    assert counts == {"주민등록번호": 1}


def test_외국인등록번호_성별코드_5_마스킹():
    masked, counts = mask_pii("외국인등록번호 850505-5678901")
    assert "[주민등록번호]" in masked
    assert counts["주민등록번호"] == 1


def test_휴대전화_구분자_변형_마스킹():
    masked, counts = mask_pii("연락처: 010-1234-5678, 010 9876 5432")
    assert masked.count("[전화번호]") == 2
    assert counts["전화번호"] == 2


def test_지역전화_마스킹():
    masked, _ = mask_pii("관리사무소 02-345-6789로 연락")
    assert "[전화번호]" in masked


def test_이메일_마스킹():
    masked, counts = mask_pii("통지처: hong.gildong+lease@example.co.kr")
    assert "[이메일]" in masked
    assert counts["이메일"] == 1


def test_카드번호_마스킹():
    masked, _ = mask_pii("결제카드 1234-5678-9012-3456")
    assert "[카드번호]" in masked


def test_계좌번호_키워드_있으면_마스킹():
    masked, counts = mask_pii("보증금 입금계좌 : 국민은행 123-456-789012 (예금주 홍길동)")
    assert "[계좌번호]" in masked
    assert "123-456-789012" not in masked
    assert counts["계좌번호"] == 1


def test_키워드_없는_숫자열은_계좌로_안_봄():
    masked, counts = mask_pii("등기번호 123-456-789012 참조")
    assert "[계좌번호]" not in masked
    assert "계좌번호" not in counts


def test_금액은_절대_안_가림():
    text = "제3조 보증금은 금 50,000,000원, 월세는 1,200,000원으로 한다."
    masked, counts = mask_pii(text)
    assert masked == text
    assert counts == {}


def test_날짜와_조항번호_보존():
    text = "제9조의2 계약 기간은 2026-09-07부터 24개월, 2기 연체 시 해지할 수 있다."
    masked, _ = mask_pii(text)
    assert masked == text


def test_고지문_생성():
    _, counts = mask_pii("주민등록번호 900101-1234567, 연락처 010-1234-5678")
    notice = masking_notice(counts)
    assert "주민등록번호 1건" in notice
    assert "전화번호 1건" in notice


def test_개인정보_없으면_고지문_없음():
    _, counts = mask_pii("제1조 임차인은 보증금을 지급한다.")
    assert masking_notice(counts) == ""
