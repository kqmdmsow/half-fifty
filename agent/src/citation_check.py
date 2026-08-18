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

# 여닫는 따옴표 쌍: 「」 『』 “” ‘’ "" ''
_QUOTE_PATTERN = re.compile(r"[「『“‘\"']([^「『“‘\"'」』”’]{5,}?)[」』”’\"']")

# 인용 내부의 중략 표기 — 분할해서 각 조각을 따로 검사한다
_ELLIPSIS_SPLIT = re.compile(r"(?:…|⋯|\.{3}|중략)")


def _normalize(s: str) -> str:
    """공백 제거 + 따옴표·괄호류 통일 — 표기 차이로 인한 오탐 방지.

    가운뎃점은 모델이 ·(U+00B7) 대신 ・(U+30FB)·․(U+FF65)로 바꿔 쓰는 사례가
    실측됨(val clause_020 폴백 원인) — 유니코드 변형까지 제거한다. 같은 이유로
    CJK 구두점(、。)과 대시류(‐–—)도 비교에서 무시한다.
    """
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[「」『』“”‘’\"'()\[\]·・･•,\.、。‐–—-]", "", s)
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


def find_fabricated_quotes(evidence: str, clause_text: str) -> List[str]:
    """조항 원문에 존재하지 않는 '원문 주장' 인용 목록을 반환한다 (빈 목록 = 통과).

    법령 출처가 명시된 인용은 검사 대상이 아니다 — 위 _LEGAL_SOURCE_MARKER 참조.
    """
    norm_clause = _normalize(clause_text)
    fabricated: List[str] = []
    for m in _QUOTE_PATTERN.finditer(evidence):
        preceding = evidence[max(0, m.start() - 60):m.start()]
        if _LEGAL_SOURCE_MARKER.search(preceding):
            continue
        for part in _ELLIPSIS_SPLIT.split(m.group(1)):
            part = part.strip()
            if len(_normalize(part)) >= 5 and _normalize(part) not in norm_clause:
                fabricated.append(part)
    return fabricated
