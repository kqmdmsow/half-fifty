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


# #70: 도메인 주입 시 모델이 문서 유형명·[표준 조항 예외] 판정 기준 문구를 출처
# 표지 없이 따옴표로 인용하면(예: "주택임대차", "2기 이상 연체 시 해지") 창작
# 인용으로 오판돼 올바른 위험 판정이 폴백됐다(주택임대차 경로 2/2 재현). #69의
# 좁은 검사 범위는 유지하고, 대신 도메인 컨텍스트 프롬프트에 "이 문구들은
# 따옴표 없이 서술하라"는 지시를 추가해 막는다 — 이 테스트는 그 지시문이
# 실수로 빠지거나, 유형명이 다시 따옴표로 래핑되는 회귀를 API 없이 잡는다.
def test_도메인_컨텍스트에_유형명_따옴표_래핑_없음():
    from src.citation_check import _QUOTE_PATTERN
    from src.nodes.analysis import _build_prompt_parts

    prefix, _ = _build_prompt_parts("주택임대차", "사용자 선택")
    start = prefix.find("[문서 유형]")
    end = prefix.find("\n\n", start)
    context_block = prefix[start:end]

    assert not _QUOTE_PATTERN.search(context_block), "도메인 컨텍스트 문구 자체에 따옴표 래핑이 있음"
    assert "따옴표" in context_block, "따옴표 금지 지시문이 빠짐"


# #59: val 재측정에서 발견된 3가지 오탐 패턴 — 신유형(v2.1) 탓이 아니라
# citation_check가 안전한 조항을 잘못 폴백시킨 것으로 확인됨 (contract_03/05,
# normal_deposit_terms — 도메인 주입과 무관, 프롬프트 전반에서 발생).

def test_조사_차이는_같은_인용으로_인정():
    """val 실측(contract_03 clause_006): 모델이 '설비에 대한 노후'를 '설비의
    노후'로 바꿔 인용해도 같은 내용 — 조사·연결어 차이는 창작 인용이 아니다."""
    clause = "임대인은 주택의 주요 설비에 대한 노후·불량으로 인한 수선 의무를 부담한다."
    evidence = "조항이 그 범위를 '주요 설비의 노후·불량'으로 한정하고 있습니다."
    assert find_fabricated_quotes(evidence, clause) == []


def test_유니코드_원점_U2024도_동일_인용_인정():
    """val 실측(contract_05 clause_004): 원문 서식이 ·(U+00B7) 대신
    ․(U+2024, ONE DOT LEADER)를 써도 같은 인용으로 인정해야 함."""
    clause = "난방, 상․하수도, 전기시설 등 임차주택의 주요설비에 대한 노후·불량으로 인한 수선은 민법 제623조"
    evidence = "조항은 '난방, 상·하수도, 전기시설 등 임차주택의 주요설비에 대한 노후·불량으로 인한 수선'을 규정합니다."
    assert find_fabricated_quotes(evidence, clause) == []


def test_risk_type_이름_자기인용은_면제():
    """val 실측(contract_05 clause_012): 모델이 자기 risk_type 이름을 설명문에서
    따옴표로 언급('~에 해당하지 않습니다')한 것을 창작 인용으로 오판하면 안 됨."""
    clause = "중개보수는 거래 가액의 %인 원으로 임대인과 임차인이 각각 부담한다."
    evidence = "수수료 산정 기준이 표준 서식에 따른 것이라 '불명확한 수수료·이자 조건'에 해당하지 않습니다."
    assert find_fabricated_quotes(evidence, clause) == []


def test_조사_관대화가_실제_창작_수치까지_봐주지_않음():
    """조사·연결어 완화가 숫자·핵심 내용이 다른 진짜 창작 인용까지 통과시키면
    안 된다 — #50 구멍 재발 방지 회귀."""
    clause = "임대인은 계약금의 10%를 위약금으로 정한다."
    evidence = "조항은 '위약금은 계약금의 50%로 정해진다'고 규정합니다."
    assert find_fabricated_quotes(evidence, clause) == ["위약금은 계약금의 50%로 정해진다"]


def test_필러토큰_제거가_무관한_내용까지_봐주지_않음():
    """'~에 대한' 같은 연결어를 지워도, 애초에 조항에 없는 핵심 단어(예: 손해배상)가
    포함된 창작 인용은 여전히 잡혀야 한다."""
    clause = "임차인은 매월 정해진 날짜에 차임을 지급한다."
    evidence = "조항은 '손해배상에 대한 별도 약정'을 두고 있다고 명시합니다."
    assert find_fabricated_quotes(evidence, clause) == ["손해배상에 대한 별도 약정"]


def test_의로_끝나는_단어는_손상되지_않음():
    """'정의'처럼 실제로 의로 끝나는 단어가 조사 제거로 훼손돼 엉뚱하게
    매칭되지 않는지 확인 (예: '정의'가 '정'으로 잘려 다른 단어와 우연히
    일치하는 사고 방지)."""
    clause = "본 계약에서 '임차인'의 정의는 별지에 따른다."
    evidence = "조항은 '임차인의 정의는 별지에 따른다'고 명시합니다."
    # 실제로 조항에 있는 내용이므로 통과해야 하며(오삭제로 인한 오탐 방지 확인),
    assert find_fabricated_quotes(evidence, clause) == []
    # 반대로 '정' 하나만으로 무관한 내용이 매칭되지는 않아야 한다.
    fabricated_evidence = "조항은 '정만 받으면 계약이 성립한다'고 명시합니다."
    assert find_fabricated_quotes(fabricated_evidence, clause) == ["정만 받으면 계약이 성립한다"]
