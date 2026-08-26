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


# ---- 판례 판정 추론 (#180 안전 표본) ---------------------------------

def test_유효_판정을_안전으로_읽는다():
    """수집 후보가 99% 위험이라 정밀도를 잴 수 없다. 안전 표본이 필요하다."""
    from collect_cases import _precedent_verdict

    assert _precedent_verdict("이는 부당하다고 볼 수 없다.")[0] == "안전"
    assert _precedent_verdict("약관법 제9조 제1호에 해당된다.")[0] == "위험"


def test_주장과_판단이_섞이면_뒤에_온_것을_결론으로_본다():
    """판결문은 "원고는 무효라 주장하나 … 부당하다고 볼 수 없다" 형태가 흔하다.

    앞 신호만 보면 정반대 라벨이 붙고, 섞였다고 전부 버리면 안전 표본을
    거의 못 건진다. 결론이 뒤에 온다는 구조를 쓰되 확신도로 표시한다.
    """
    from collect_cases import _precedent_verdict

    v, how = _precedent_verdict("원고는 무효라고 주장하나, 부당하다고 볼 수 없다.")
    assert (v, how) == ("안전", "신호 혼재")
    v, how = _precedent_verdict("피고는 유효하다고 주장하나, 신의성실의 원칙에 반한다.")
    assert (v, how) == ("위험", "신호 혼재")


def test_판단_신호가_없으면_판정하지_않는다():
    from collect_cases import _precedent_verdict

    assert _precedent_verdict("이 사건 계약 제3조는 보증금을 정하고 있다.") == ("", "")


def test_조_번호가_없어도_조항을_뽑는다():
    """판결문은 "이 사건 조항은 …라고 정한다"처럼 번호 없이 쓰는 일이 흔하다.

    번호를 요구했더니 실측 수율이 79건 중 1건으로 떨어졌다.
    """
    body = ('이 사건 조항은 "회원이 탈퇴하는 경우 잔여 기간에 대한 환불은 '
            '하지 아니한다"라고 정하고 있다. 이는 부당하다고 볼 수 없다.')
    out = extract_precedent_clauses(body)
    assert out and out[0]["verdict"] == "안전"
    assert out[0]["article_no"] == ""


def test_인용문_앞의_조사와_따옴표를_떼어_낸다():
    # '제9조**는 "**어떠한 경우에도…' 처럼 군더더기가 딸려 오면 원문 대조가 깨진다.
    body = '이 사건 약관 제9조는 "어떠한 경우에도 보증금을 반환하지 아니한다"라고 규정한다.'
    out = extract_precedent_clauses(body)
    assert out[0]["clause_text"].startswith("어떠한 경우에도")
    assert not out[0]["clause_text"].endswith('"')


def test_판결문_서술_조각은_조항으로_보지_않는다():
    """앵커가 문장 중간에 걸리면 판결문 서술이 딸려 온다."""
    from collect_cases import is_clause_like

    assert not is_clause_like("라 한다), 2020. 1. 29. 피고와 사이에 분담금을 정하여")
    assert not is_clause_like("2019. 1. 15. 계약을 체결하였다")


def test_원고_피고가_들어가도_조항일_수_있다():
    """판결문은 계약 당사자를 원고·피고로 바꿔 인용한다.

    이걸 서술 신호로 쓰면 정상 약관 조항이 대량으로 날아간다.
    """
    from collect_cases import is_clause_like

    assert is_clause_like("기타 원고의 단독 재량으로 계정의 해지가 필요하다고 판단하는 경우")


# ---- 검수 파이프라인 (#180) ------------------------------------------

def test_원문에_없는_제안은_통과하지_못한다():
    """축자 원문 부재는 실측 기각 사유 2위다. 요약·의역은 골든셋에 들어가면 안 된다."""
    from review_pipeline import _verbatim

    src = "피심인은 어떠한 경우에도 환불하지 아니한다고 규정하고 있다."
    assert _verbatim("어떠한 경우에도 환불하지 아니한다", src)
    assert not _verbatim("환불을 전면 금지하는 조항", src)   # 의역


def test_검수_실패는_승인이_아니다():
    """확인하지 못한 것을 통과시키면 검수가 아니라 통과 도장이 된다."""
    import review_pipeline as rp

    orig = rp.invoke_json
    rp.invoke_json = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    rp.get_worker_llm = lambda: None
    try:
        assert rp.adversarial_review({}, "자료")["verdict"] == "기각"
    finally:
        rp.invoke_json = orig


def test_제안_실패도_기각으로_처리한다():
    import review_pipeline as rp

    orig = rp.invoke_json
    rp.invoke_json = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    rp.get_worker_llm = lambda: None
    try:
        assert rp.propose({})["proposable"] is False
    finally:
        rp.invoke_json = orig


def test_조항_문구가_없으면_LLM을_부르지_않고_기각한다():
    # 비용을 아끼는 동시에, 문구 없는 후보가 통과할 여지를 원천 차단한다.
    from review_pipeline import review_one

    r = review_one({"rationale": "판단 근거"}, set())
    assert r["verdict"] == "자동기각" and r["reason"] == "축자 원문 부재"


def test_기존_골든셋과_중복이면_기각한다():
    from review_pipeline import review_one

    r = review_one({"clause_text": "어떠한 경우에도 환불하지 아니한다",
                    "rationale": "x"}, {"어떠한경우에도환불하지아니한다"})
    assert r["verdict"] == "자동기각" and "중복" in r["reason"]


def test_검수단_2표_기각이면_탈락한다():
    """만장일치를 요구하면 통과율이 비현실적으로 낮아지고,
    과반만 보면 한 에이전트의 실수가 그대로 통과한다."""
    import review_pipeline as rp

    assert rp._REVIEWERS == 3 and rp._REJECT_VOTES == 2


def test_기관의_설명은_조항으로_보지_않는다():
    """가장 놓치기 쉬운 유형이다. 기관이 그 조항을 설명한 말은 근거 서술에
    그대로 있으므로 **원문 대조를 통과한다.** 실측 표본 18건 중 3건이 이것이었다.

    조항은 규범을 정하고, 설명은 그 조항을 평가한다.
    """
    from collect_cases import is_clause_like

    assert not is_clause_like(
        "회원탈퇴에 대한 전제조건으로 3개월 이상을 사용하도록 정하여 자유로운 탈퇴를 상당히 제한하고 있으므로")
    assert not is_clause_like("회사가 인정하는 사유가 있는 경우에만 탈퇴를 허용하는 것")
    assert not is_clause_like("해당 시간 영업 손해에 대한 비용")   # 문구 조각


def test_정상_조항은_통과한다():
    from collect_cases import is_clause_like

    assert is_clause_like("보증금은 어떠한 경우에도 반환하지 아니한다")
    assert is_clause_like("임차인이 임대료 등을 연체할 경우 연체이자율은 월 5%로 하며 일할계산하여 부과한다")
