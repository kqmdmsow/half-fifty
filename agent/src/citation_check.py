"""인용 근거 원문 존재 검사 (규칙 기반, LLM 불요).

전문가 자문 §5: "인용한 근거가 원문에 존재하는지는 규칙으로 확인" —
risk_evidence가 따옴표로 원문을 인용할 때, 그 인용이 조항 원문에 실제로
존재하는지 코드로 검증한다. 존재하지 않는 인용(창작 인용)은 faithfulness
위반의 가장 명백한 형태인데, LLM Judge에 맡기면 확률적으로만 잡힌다.

규칙 범위: 명시적 따옴표 인용(「」, "", '', “” 등)만 검사한다. 따옴표 없는
의역·요약은 검사하지 않는다 (의역 자유는 보장, 명시 인용의 정확성만 강제).
비교는 공백·따옴표 종류 차이를 무시하는 정규화 문자열 포함 검사로 한다.
"""

import re
from typing import List

from src.schemas import RISK_TYPES

# 여닫는 따옴표 쌍: 「」 『』 “” ‘’ "" ''
_QUOTE_PATTERN = re.compile(r"[「『“‘\"']([^「『“‘\"'」』”’]{5,}?)[」』”’\"']")

# 인용 내부의 중략 표기 — 분할해서 각 조각을 따로 검사한다
_ELLIPSIS_SPLIT = re.compile(r"(?:…|⋯|\.{3}|중략)")

# 조사(단어 끝에 붙는 것만 제거 — 단어 중간·시작의 동일 글자는 안 건드림).
# 긴 조사부터 매칭해야 짧은 조사가 먼저 걸려 앞부분이 남는 사고를 막는다
# (예: "으로서"를 "로"보다 먼저 검사).
_JOSA_SUFFIXES = (
    "으로서", "으로써", "이라는", "라는", "에서는", "에게는",
    "으로는", "로는", "에는", "에서", "에게", "께서", "이나", "부터", "까지",
    "보다", "처럼", "같이", "만큼", "마저", "조차",
    "으로", "로", "은", "는", "이", "가", "을", "를", "의", "에", "도", "만", "나",
)
# 독립 토큰으로만 등장할 때 통째로 제거하는 연결어(의존명사+조사 결합형).
# "~에 대한/관한/의한/따른" 류 — 조사 대체 표현으로 흔히 쓰이지만 접미사가
# 아니라 별도 토큰이라 위 리스트로는 못 잡는다.
_FILLER_TOKENS = frozenset({
    "대한", "대하여", "관한", "관하여", "의한", "의하여", "따른", "따라",
    "위한", "위하여", "인한", "인하여",
})

# 목적어로 쓰인 지시대명사 — 완전한 조사 결합형(이+를, 그것+을)으로만
# 매칭한다. 대명사 어근("이", "그")은 넣지 않는다: "이 조항"처럼 뒤 명사를
# 꾸미는 관형사로도 흔히 쓰여서, 어근만 지우면 무관한 단어까지 훼손될
# 위험이 크다(#78 데모 리허설 실측: normal_deposit_terms clause_014
# "은행이 이를 접수한 뒤"를 모델이 "은행이 접수한 뒤"로 인용해 폴백됨).
# 그 외 변형(새 단어 추가·순서 변경·다른 문구)은 여전히 엄격하게 검사한다.
_PRONOUN_FILLER_TOKENS = frozenset({"이를", "그를", "이것을", "그것을"})


def _strip_josa(token: str) -> str:
    for suf in _JOSA_SUFFIXES:
        if token.endswith(suf) and len(token) > len(suf):
            return token[: -len(suf)]
    return token


def _normalize(s: str) -> str:
    """공백 제거 + 조사·연결어·따옴표류 통일 — 표기·사소한 어미 차이로 인한 오탐 방지.

    가운뎃점은 모델이 ·(U+00B7) 대신 ・(U+30FB)·･(U+FF65)·․(U+2024)로 바꿔
    쓰거나 원문 자체가 그렇게 조판된 사례가 실측됨(val clause_020, contract_05
    clause_004) — 유니코드 변형까지 제거한다. 같은 이유로 CJK 구두점(、。)과
    대시류(‐–—)도 비교에서 무시한다.

    조사(은/는/이/가/을/를/의/에/으로 등)와 "~에 대한/관한/따른" 류 연결어는
    공백 기준 토큰 단위로만 제거한다(단어 중간 글자는 안 건드려 "정의"→"정"
    같은 오삭제를 피한다) — val 실측(contract_03 clause_006: "설비에 대한
    노후"를 모델이 "설비의 노후"로 바꿔 쓴 사례)이 근거.
    """
    tokens = s.split()
    kept = []
    for tok in tokens:
        trailing = ""
        core = tok
        while core and not core[-1].isalnum():  # Hangul 음절도 isalnum()=True
            trailing = core[-1] + trailing
            core = core[:-1]
        if core in _FILLER_TOKENS or core in _PRONOUN_FILLER_TOKENS:
            continue
        kept.append(_strip_josa(core) + trailing)
    s = "".join(kept)
    s = re.sub(r"[「」『』“”‘’\"'()\[\]·・･•․,\.、。‐–—-]", "", s)
    return s


def extract_quotes(evidence: str) -> List[str]:
    """risk_evidence에서 명시적 따옴표 인용 조각들을 추출한다 (5자 미만 제외)."""
    quotes: List[str] = []
    for m in _QUOTE_PATTERN.finditer(evidence):
        for part in _ELLIPSIS_SPLIT.split(m.group(1)):
            part = part.strip()
            if len(_normalize(part)) >= 5:
                quotes.append(part)
    return quotes


# 법령·판례 출처 표지가 인용 직전(40자 이내)에 있으면 계약 원문 인용이 아니라
# 외부 법지식 인용이다 — faithfulness 루브릭 명확화("외부 법지식 인용 ≠ 위반")와
# 동일 원칙으로 하드페일 대상에서 제외한다 (그 인용의 정확성은 Judge 소관).
# 실측 사례(#49 도메인 주입 후): "상가건물임대차보호법 제10조는 '3기의 차임액…'을
# 규정" — 정확한 법령 인용이 원문 부재로 오판되어 올바른 위험 판정이 폴백됐다.
_LEGAL_SOURCE_MARKER = re.compile(
    r"(민법|보호법|약관규제법|임대차보호법|자본시장법|근로기준법|법률|판례|표준계약서"
    r"|제\s?\d+\s?조(의\s?\d+)?).{0,40}$"
)

# risk_type 카테고리 이름 자체를 설명문에서 따옴표로 인용하는 경우(예: "이 조항은
# '불명확한 수수료·이자 조건'에 해당하지 않습니다") — 조항 원문 주장이 아니라
# 분류 체계 용어 언급이라 창작 인용이 아니다. val 실측(contract_05 clause_012)에서
# 이걸 못 걸러 안전한 조항이 폴백된 사례 확인. 정확히 일치할 때만 면제한다(#59).
_RISK_TYPE_NAMES_NORMALIZED = frozenset(_normalize(name) for name in RISK_TYPES)

# analysis.txt [표준 조항 예외](62~68행)가 따옴표로 감싸 제시하는 차임 연체
# 판정 기준 문구 자체 — risk_type 이름과 동일한 성격(조항 원문 주장이 아니라
# 프롬프트가 정의한 분류 기준 용어 인용)이라 같은 방식으로 면제한다(#73).
# #70(도메인 컨텍스트, _DOMAIN_CONTEXT_KNOWN)과 달리 이 문구는 도메인 미주입
# 경로를 포함한 analysis.txt 본문에 항상 존재해, 프롬프트 쪽 "따옴표 없이
# 서술" 지시로는 무도메인 프롬프트 바이트 단위 보존 원칙(#69)을 지킬 수
# 없다 — citation_check 쪽에서 정확히 일치할 때만 면제하는 쪽이 프롬프트를
# 건드리지 않고 문제를 근본적으로 막는다. 문구가 바뀌면 이 목록도 같이
# 갱신해야 하며, test_citation_check.py가 analysis.txt 본문에 이 문구들이
# 실제로 존재하는지 확인해 드리프트를 잡는다.
_STANDARD_CLAUSE_EXCEPTION_PHRASES = (
    "2기(2개월) 이상 연체 시 해지",
    "3기 연체",
    "2기 연체 해지",
    "3기 연체 해지",
)
_STANDARD_CLAUSE_EXCEPTION_NORMALIZED = frozenset(
    _normalize(p) for p in _STANDARD_CLAUSE_EXCEPTION_PHRASES
)


def find_fabricated_quotes(evidence: str, clause_text: str) -> List[str]:
    """조항 원문에 존재하지 않는 '원문 주장' 인용 목록을 반환한다 (빈 목록 = 통과).

    법령 출처가 명시된 인용, risk_type 카테고리 이름·[표준 조항 예외] 판정
    기준 문구 자체의 인용은 검사 대상이 아니다 — 위 _LEGAL_SOURCE_MARKER·
    _RISK_TYPE_NAMES_NORMALIZED·_STANDARD_CLAUSE_EXCEPTION_NORMALIZED 참조.
    """
    norm_clause = _normalize(clause_text)
    fabricated: List[str] = []
    for m in _QUOTE_PATTERN.finditer(evidence):
        preceding = evidence[max(0, m.start() - 60):m.start()]
        if _LEGAL_SOURCE_MARKER.search(preceding):
            continue
        for part in _ELLIPSIS_SPLIT.split(m.group(1)):
            part = part.strip()
            norm_part = _normalize(part)
            if len(norm_part) < 5:
                continue
            if norm_part in _RISK_TYPE_NAMES_NORMALIZED:
                continue
            if norm_part in _STANDARD_CLAUSE_EXCEPTION_NORMALIZED:
                continue
            if norm_part not in norm_clause:
                fabricated.append(part)
    return fabricated
