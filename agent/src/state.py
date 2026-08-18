"""파이프라인 전체를 관통하는 상태(State) 정의.

착수보고서 <표 4> 단계별 입출력을 그대로 코드로 옮긴 것.
LangGraph의 모든 노드는 이 PipelineState를 입력받고 일부 필드를 갱신해 반환한다.
"""

from typing import Dict, List, Literal, TypedDict


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
    rationale: dict[str, str]  # aspect별 채점 근거 (사람-LLM 상관도 분석용)


JUDGE_ASPECT_KEYS = ("clarity", "faithfulness", "risk_coverage", "actionability")


def judge_score_avg(scores: "JudgeScores") -> float:
    """rationale을 제외한 4개 수치 aspect의 평균 (재시도 임계값 판정용)."""
    return sum(scores[k] for k in JUDGE_ASPECT_KEYS) / len(JUDGE_ASPECT_KEYS)


def failing_aspects(scores: "JudgeScores") -> List[str]:
    """임계 미달 aspect 목록 (JUDGE_ASPECT_KEYS 순서 유지)."""
    return [k for k in JUDGE_ASPECT_KEYS if scores[k] < JUDGE_THRESHOLD]


def shortcut_eligible(scores: "JudgeScores") -> bool:
    """clarity-only 재생성 단축 허용 조건 (자문 §3 대응, #75/#35).

    risk_coverage·faithfulness가 임계값을 근소하게만 넘긴 상태에서 clarity만
    고쳐 persona만 재실행하고 재채점하면, Judge 채점 노이즈로 원래
    재검증됐어야 할 위험 오분류가 "우연히 또 통과"하며 새어나간다(#35 실측:
    데모 5건 FP 3→7, contract_05는 재시도 2→0 + needs_review True→False로
    바뀌었는데 Judge 평균은 오히려 상승 — "품질 개선"이 아니라 눈속임).
    risk_coverage·faithfulness가 임계값보다 확실히 위(+RETRY_SHORTCUT_MARGIN)
    일 때만 단축을 허용한다 — 아슬아슬하면 analysis 전체 재실행으로 보낸다.
    """
    return (
        scores["risk_coverage"] >= JUDGE_THRESHOLD + RETRY_SHORTCUT_MARGIN
        and scores["faithfulness"] >= JUDGE_THRESHOLD + RETRY_SHORTCUT_MARGIN
    )


class PipelineState(TypedDict):
    """그래프 전체 상태."""

    # 입력
    raw_text: str
    persona: Literal["adult", "senior", "foreigner"]
    language: str  # 설명 출력 언어 (ko/en/zh/vi — persona 노드에서만 사용, 기본 "ko")

    # 각 단계 출력
    domain: str             # 문서 유형 (사용자 선택 또는 자동 판별, 실패 시 "알 수 없음")
    domain_evidence: str    # 판별 근거 (사용자 선택이면 "사용자 선택")
    parse_warnings: List[str]  # Parser 추출 경고 (별지 제외, 커버리지 미달 등)
    clauses: List[Clause]
    analysis_results: List[AnalysisResult]
    adapted_results: List[AnalysisResult]  # 페르소나 적응 후
    judge_scores: JudgeScores

    # 비한국어 언어 선택 시 조항 원문·확인 질문 번역 (clause_id -> 번역 dict).
    # adapted_results와 분리하는 이유: Judge 입력에 낯선 필드를 섞지 않기 위함.
    translations: Dict[str, dict]

    # 재생성 루프 제어 (착수보고서: 최대 2회 재실행)
    retry_count: int
    needs_review: bool  # 재시도 소진 후에도 기준 미달이면 True ("주의 필요" 플래그)


# Judge 평균 점수가 이 값 미만이면 Analysis 재실행 (실험하며 조정)
JUDGE_THRESHOLD = 3.5
# faithfulness 필수 조건 (자문 §5): 평균이 높아도 원문 왜곡·창작 근거가 있으면
# 통과 금지 — 평균이 치명 결함을 은폐하는 것을 막는 hard-fail 기준.
FAITHFULNESS_MIN = 3.0
MAX_RETRIES = 2
# clarity-only 재생성 단축(shortcut_eligible) 허용 마진 — #75/#35.
RETRY_SHORTCUT_MARGIN = 1.0
