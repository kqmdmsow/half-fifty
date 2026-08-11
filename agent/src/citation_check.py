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
    """공백 제거 + 따옴표·괄호류 통일 — 표기 차이로 인한 오탐 방지."""
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[「」『』“”‘’\"'()\[\]·,\.]", "", s)
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


def find_fabricated_quotes(evidence: str, clause_text: str) -> List[str]:
    """조항 원문에 존재하지 않는 인용 조각 목록을 반환한다 (빈 목록 = 통과)."""
    norm_clause = _normalize(clause_text)
    return [q for q in extract_quotes(evidence) if _normalize(q) not in norm_clause]
