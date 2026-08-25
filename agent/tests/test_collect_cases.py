"""공개 심결·판례 수집 파이프라인 (#180).

자동 수집이 만들 수 있는 최악의 사고는 **잘못된 라벨이 조용히 골든셋에 들어가는
것**이다. 그 위에서 잰 모든 수치가 의미를 잃는다. 그래서 여기서는 "무엇을
수집했는가"보다 **"무엇을 걸러냈는가"**를 고정한다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from collect_cases import (_ARTICLE_TO_TYPES, _OPINION_TO_LEVEL, _entry,
                           extract_precedent_clauses, parse_decision)

# ---- 공정위 심결 파싱 ------------------------------------------------

A형 = """2. 중도해지 불가조항
가. 약관조항
나. 심사의견 : 부분 무효
○ 고객의 중도해지를 제한하는 약관조항은 약관법 제9조 제1호에 해당된다.
"""
B형 = """2. 심사결과 : 무효
고객에게 환불을 전혀 해 주지 않는다고 규정한 것은 약관법 제9조 제3호에 해당된다.
"""
C형 = """2. 위약금 조항
가. 약관조항
다. 판단
임대보증금 납부 이전의 계약해제권을 부당하게 제한하고 있으므로 약관법 제9조 제1호에 해당된다.
"""


def test_A형_심사의견_명시를_읽는다():
    out = parse_decision(A형)
    assert len(out) == 1
    assert out[0]["opinion"] == "부분 무효"
    assert out[0]["gold_risk_level_candidate"] == "주의"
    assert out[0]["opinion_source"] == "명시"


def test_B형_심사결과도_읽는다():
    # 형식이 하나가 아니다. B형을 버리면 헬스장 건이 통째로 날아간다.
    out = parse_decision(B형)
    assert out and out[0]["gold_risk_level_candidate"] == "위험"


def test_C형은_조문_인용으로_추론하되_표시한다():
    """판정 라벨 없이 조문만 인용하는 형식. 추론임을 반드시 남긴다."""
    out = parse_decision(C형)
    assert out and out[0]["gold_risk_level_candidate"] == "위험"
    assert out[0]["opinion_source"] == "조문인용 추론"


def test_부정형은_유효로_읽는다():
    seg = "다. 판단\n부당하다고 볼 수 없으므로 약관법 제9조에 해당되지 않는다."
    assert _entry("x", seg)["gold_risk_level_candidate"] == "안전"


def test_판정_신호가_없으면_후보로_내지_않는다():
    assert parse_decision("1. 계약 개요\n피심인은 체육시설업을 영위한다.") == []


def test_조문이_여러_유형에_걸리면_나열한다():
    # 검수자가 하나를 고르게 한다. 자동으로 하나를 찍으면 오라벨이 된다.
    out = _entry("x", "약관법 제6조에 해당된다. 심사의견 : 무효")
    assert len(out["gold_risk_type_candidates"].split("|")) > 1


def test_부분무효는_주의로_보수적으로_매핑한다():
    # 일부라도 무효면 사용자가 확인할 이유가 있다. '안전'은
    # "확인하지 않아도 된다"는 뜻이므로 거기 넣으면 안 된다.
    assert _OPINION_TO_LEVEL["부분무효"] == "주의"
    assert _OPINION_TO_LEVEL["무효"] == "위험"
    assert _OPINION_TO_LEVEL["유효"] == "안전"


# ---- 판례 조항 인용 추출 ---------------------------------------------

def test_계약_조항_인용을_뽑는다():
    body = ('이 사건 이용약관 제23조 제2항은 "기타 원고의 단독 재량으로 계정의 '
            '해지 또는 정지가 필요하다고 판단하는 경우"라고 정하고 있다.')
    out = extract_precedent_clauses(body)
    assert out and "단독 재량" in out[0]["clause_text"]


def test_법령_인용은_계약_조항으로_수집하지_않는다():
    """민법 조문을 계약 조항으로 넣으면 골든셋이 오염된다."""
    body = ('민법 제741조는 "법률상 원인 없이 타인의 재산으로 이익을 얻고 '
            '타인에게 손해를 가한 자는 그 이익을 반환하여야 한다."라고 정하고 있다.')
    assert extract_precedent_clauses(body) == []


def test_법원의_판단_서술은_조항이_아니다():
    body = ('이 사건 이용약관 제23조에 따라 "이 사건 이용제한조치는 적법하다고 '
            '인정된다. 따라서 원고의 주장은 이유 없다"라고 판단하였다.')
    assert extract_precedent_clauses(body) == []


def test_같은_인용은_한_번만_낸다():
    q = '이 사건 계약 제5조는 "보증금은 어떠한 경우에도 반환하지 아니한다"라고 정한다. '
    assert len(extract_precedent_clauses(q * 3)) == 1
