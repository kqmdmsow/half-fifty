"""파이프라인 전체를 관통하는 상태(State) 정의.

착수보고서 <표 4> 단계별 입출력을 그대로 코드로 옮긴 것.
LangGraph의 모든 노드는 이 PipelineState를 입력받고 일부 필드를 갱신해 반환한다.
"""

from typing import List, Literal, TypedDict


class Clause(TypedDict):
    """Parser Module의 출력 단위 (조항)."""

    clause_id: str  # 예: "clause_001"
    text: str       # 조항 원문


class AnalysisResult(TypedDict):
    """Analysis Agent의 4종 출력 (조항 1개당 1개)."""

    clause_id: str
    explanation: str        # ① 쉬운 설명
    risk_level: Literal["안전", "주의", "위험"]  # ② 위험 여부
    risk_type: str          # ② 위험 유형 (없으면 "해당 없음")
    risk_evidence: str      # ③ 위험 근거
    check_questions: List[str]  # ④ 사용자가 확인해야 할 질문


class JudgeScores(TypedDict):
    """Judge Agent의 4 Aspect 점수 (1~5점)."""

    clarity: float          # 이해용이성
    faithfulness: float     # 충실성 (환각 여부)
    risk_coverage: float    # 위험 식별
    actionability: float    # 행동 지침


class PipelineState(TypedDict):
    """그래프 전체 상태."""

    # 입력
    raw_text: str
    persona: Literal["adult", "senior"]

    # 각 단계 출력
    clauses: List[Clause]
    analysis_results: List[AnalysisResult]
    adapted_results: List[AnalysisResult]  # 페르소나 적응 후
    judge_scores: JudgeScores

    # 재생성 루프 제어 (착수보고서: 최대 2회 재실행)
    retry_count: int
    needs_review: bool  # 재시도 소진 후에도 기준 미달이면 True ("주의 필요" 플래그)


# Judge 평균 점수가 이 값 미만이면 Analysis 재실행 (실험하며 조정)
JUDGE_THRESHOLD = 3.5
MAX_RETRIES = 2
