"""Parser 실물 문서 회귀 테스트 (#79).

기존 test_parser.py는 전부 자작 계약서(data/*.txt, AI-Hub 스타일 합성
샘플) 기반이라 자문 §2 "실제 계약서를 기반으로 회귀 테스트를 확대해야
합니다" 지적이 미해결이었다. data/raw/는 실제 약관·공정위/금감원
분쟁조정 사례 원문이라 형식이 표준계약서와 다르고(사건개요·당사자
주장 등 서사가 섞여 있거나, 조항이 "제N조" 없이 원문 요약만 있는 등),
지금까지 코드가 검증된 적 없는 입력 형태다. 이 테스트는 파서를 고치지
않고 **현재 동작을 golden으로 고정**한다 — 조항 수·핵심 문구 보존이
기준이며, 그 자체로 알려진 결함(별표 결합 등, #79)까지 있는 그대로
잠근다. #79의 별표 독립 분리 작업이 진행되면 이 테스트도 함께
갱신해야 한다.
"""

from pathlib import Path

from src.nodes.parser import split_clauses_with_warnings

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw"


def _parse(filename):
    text = (RAW_DIR / filename).read_text(encoding="utf-8")
    return split_clauses_with_warnings(text)


def test_예금거래기본약관_25개_조항_경고없이_분리():
    """별표·부칙이 없는 깨끗한 25개조 실물 약관 — 표준계약서 형식과 가장 가까운 대조군."""
    clauses, warnings = _parse("10012_예금거래기본약관.txt")
    assert len(clauses) == 25
    assert warnings == []
    assert clauses[0]["text"].startswith("제1조(적용범위)")
    assert clauses[-1]["text"].startswith("제24조(위법계약의 해지)")


def test_즉시연금_공시이율_조항까지_4개_분리():
    clauses, warnings = _parse("2017-17_즉시연금_최저보증이율.txt")
    assert len(clauses) == 4
    assert clauses[0]["text"].startswith("제3조(계약의 체결 및 보험료)")
    assert "만기보험금" in clauses[1]["text"]


def test_즉시연금_별표가_앞_조항_꼬리에_결합됨_기존동작_고정():
    """알려진 결함(#79): 별표1이 독립 청크로 승격되지 못하고 제17조 뒤에
    그대로 붙어 살아남는다. 별표 분리 작업 착수 전까지는 이 동작이
    "정상"이므로, 조용히 달라지면(예: 우연한 회귀로 별표가 아예 유실되면)
    바로 잡아내기 위해 길이 하한을 고정한다."""
    clauses, warnings = _parse("2017-17_즉시연금_최저보증이율.txt")
    last = clauses[-1]
    assert last["text"].startswith("제17조(해지환급금)")
    assert len(last["text"]) > 1500  # 별표1 내용이 유실되지 않고 결합돼 있음


def test_바로연금보험_만기보험금_지급사유_조항_보존():
    clauses, warnings = _parse("2018-8_바로연금보험_환급플랜.txt")
    assert len(clauses) == 4
    assert "만기보험금" in clauses[2]["text"]
    assert clauses[2]["text"].startswith("제3조(보험금의 지급사유)")


def test_바로연금보험_별표가_앞_조항_꼬리에_결합됨_기존동작_고정():
    clauses, warnings = _parse("2018-8_바로연금보험_환급플랜.txt")
    last = clauses[-1]
    assert last["text"].startswith("제6조(공시이율의 적용 및 공시)")
    assert len(last["text"]) > 1800


def test_보험업_제재금공제_조항표제없는_요약문은_통짜로_보존():
    """분쟁조정 사례 요약본은 "제N조" 표제 자체가 없어(원문 발췌가 아니라
    요약) 분리 지점이 없다 — 전체가 조항 1건으로 보존돼야 하며 내용
    손실이 없어야 한다(경고도 없음: 커버리지 100%)."""
    clauses, warnings = _parse("2014-02_보험업_제재금공제.txt")
    assert len(clauses) == 1
    assert warnings == []
    assert "제재금" in clauses[0]["text"]


def test_신발도매업_사례문서에서_임베디드_조항만_추출되고_경고발생():
    """공정위 사례 원문은 사건개요·당사자 주장 서사에 실제 약관조항(제4조)이
    파묻혀 있다 — 파서는 그 조항만 정확히 뽑아내고, 서사 부분이 조항으로
    분리되지 않았다는 저커버리지 경고를 내야 한다(조용한 누락 금지 원칙)."""
    clauses, warnings = _parse("2013_신발도매업_해지위약금.txt")
    assert len(clauses) == 1
    assert clauses[0]["text"].startswith("제4조(가맹금 등 금전의 반환조건에 관한 사항)")
    assert "위약벌" in clauses[0]["text"]
    assert len(warnings) == 1


def test_광고대행업_사례문서에서_임베디드_조항만_추출되고_경고발생():
    clauses, warnings = _parse("2025-03_광고대행업_중도해지.txt")
    assert len(clauses) == 1
    assert clauses[0]["text"].startswith("제10조")
    assert "20%" in clauses[0]["text"]
    assert len(warnings) == 1


def test_유선통신업_사례문서는_조항표제없이_법령_참조만_있어_0건():
    """알려진 gap(#79 작업 중 발견, 별도 이슈 후보): 이 문서는 "제N조" 줄
    시작 표제가 전혀 없고 본문 중간에 "약관규제법 제12조"처럼 법령
    조번호를 참조하는 문장만 있다. has_articles 판정(비anchored 정규식)이
    이를 "조문 있음"으로 오인해, 정작 anchored _ARTICLE_PATTERN에는 아무
    청크도 매칭되지 않는 조합 때문에 조항 0건 + 저커버리지 경고로
    떨어진다 — 2014-02(조 표제 자체가 없는 문서)와 다르게 이 문서만
    이렇게 되는 비대칭이 있다는 걸 여기 고정해 둔다."""
    clauses, warnings = _parse("2013_유선통신업_보증기간연장.txt")
    assert len(clauses) == 0
    assert len(warnings) == 1
