"""LLM 출력 런타임 검증 (Pydantic).

왜 필요한가: `AnalysisResult`는 TypedDict라 런타임 검증이 없어, 모델이 스키마를
벗어난 출력(예: risk_type을 리스트로, "10. 권리행사 제한"처럼 번호 붙여서)을
내도 그대로 통과했다. 유형이 6→10종으로 늘며 다중 유형 반환 빈도가 증가해
(docs/risk_taxonomy_v2.md), 팀 합의로 최우선 도입. 전문가 자문(§5 "JSON 형식과
필수 필드는 코드로 검사")과도 일치.

검증 실패는 예외로 올려 _analyze_clause의 기존 재시도 루프에 태운다 —
잘못된 출력을 고쳐 쓰는 게 아니라, 재생성 기회를 준 뒤 폴백시키는 구조.
단, 의미가 보존되는 사소한 이탈(리스트 반환, 번호 접두사)은 정규화로 흡수해
불필요한 재시도·폴백을 막는다.
"""

import re
from typing import List, Literal

from pydantic import BaseModel, field_validator

# analysis.txt [위험 유형 기준]과 동일하게 유지할 것 (10종 + 해당 없음)
RISK_TYPES = (
    "과도한 위약금",
    "일방적 계약 해지",
    "보증금 반환 지연",
    "책임 면제",
    "불명확한 수수료·이자 조건",
    "신탁관계·소유권 불안정 고지",
    "부당한 비용·세금 전가",
    "일방적 급부·조건 변경",
    "선택권 제한·구입 강제",
    "권리행사 제한",
    "해당 없음",
)


class AnalysisOutput(BaseModel):
    """Analysis Agent 출력의 런타임 스키마."""

    explanation: str
    risk_level: Literal["안전", "주의", "위험"]
    risk_type: str
    risk_evidence: str
    check_questions: List[str]

    @field_validator("risk_type", mode="before")
    @classmethod
    def _normalize_risk_type(cls, v):
        # 다중 유형 반환 시 첫 항목을 주 유형으로 채택 (프롬프트는 단일 유형 지시)
        if isinstance(v, (list, tuple)):
            v = v[0] if v else "해당 없음"
        v = str(v).strip()
        # "10. 권리행사 제한" / "2. 일방적 계약 해지" 같은 번호 접두사 제거
        v = re.sub(r"^\d+\s*[.)]\s*", "", v)
        return v

    @field_validator("check_questions", mode="before")
    @classmethod
    def _coerce_questions(cls, v):
        # 문자열 하나로 반환하는 경우 리스트로 승격
        if isinstance(v, str):
            return [v]
        return v

    @field_validator("explanation", "risk_evidence")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("빈 문자열")
        return v
