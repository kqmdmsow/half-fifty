"""Analysis Agent: 조항별 4종 출력 생성.

① 쉬운 설명 ② 위험 여부/유형 ③ 위험 근거 ④ 확인 질문

현재는 더미 구현. LLM 연동 시 아래 순서로 교체:
  1. src/prompts/analysis.txt 프롬프트 로드
  2. 조항별로 LLM 호출 (JSON 출력 강제)
  3. AnalysisResult 스키마로 파싱
"""

from pathlib import Path
from typing import List

from src.state import AnalysisResult, PipelineState

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "analysis.txt"

# 착수보고서에 정의된 위험 유형 (프롬프트에 주입할 기준)
RISK_TYPES = [
    "과도한 위약금",
    "일방적 계약 해지",
    "보증금 반환 지연",
    "책임 면제",
    "불명확한 수수료·이자 조건",
]

# 더미용 간단 키워드 매칭 (LLM 붙이기 전 파이프라인 검증 목적)
_KEYWORD_TO_RISK = {
    "위약금": "과도한 위약금",
    "해지": "일방적 계약 해지",
    "보증금": "보증금 반환 지연",
    "면책": "책임 면제",
    "책임을 지지 않": "책임 면제",
    "수수료": "불명확한 수수료·이자 조건",
    "이자": "불명확한 수수료·이자 조건",
}


def _analyze_clause_dummy(clause_id: str, text: str) -> AnalysisResult:
    """LLM 없이 동작하는 더미 분석. 키워드가 있으면 '주의'로 표시."""
    risk_type = "해당 없음"
    risk_level = "안전"
    evidence = "위험 키워드가 발견되지 않았습니다. (더미 판정)"

    for keyword, mapped in _KEYWORD_TO_RISK.items():
        if keyword in text:
            risk_type = mapped
            risk_level = "주의"
            evidence = f"조항에 '{keyword}' 관련 표현이 포함되어 있습니다. (더미 판정)"
            break

    return AnalysisResult(
        clause_id=clause_id,
        explanation=f"[더미 설명] 이 조항은 다음 내용을 담고 있습니다: {text[:40]}...",
        risk_level=risk_level,
        risk_type=risk_type,
        risk_evidence=evidence,
        check_questions=[
            "[더미 질문] 이 조항의 조건이 나에게 불리하지 않은지 상대방에게 확인했나요?",
        ],
    )


def analysis_node(state: PipelineState) -> dict:
    """LangGraph 노드: clauses -> analysis_results.

    TODO(민제): LLM 연동 시 _analyze_clause_dummy 를 실제 LLM 호출로 교체.
      from langchain_anthropic import ChatAnthropic  # 또는 langchain_openai
      prompt = PROMPT_PATH.read_text(encoding="utf-8")
      ...
    """
    results: List[AnalysisResult] = [
        _analyze_clause_dummy(c["clause_id"], c["text"]) for c in state["clauses"]
    ]
    return {"analysis_results": results}
