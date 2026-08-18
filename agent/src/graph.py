"""LangGraph 5단계 파이프라인 조립 (착수보고서 <그림 3> + Domain 확장).

Parser(Module) -> Domain(Agent) -> Analysis(Agent) -> Persona(Agent) -> Judge(Agent)
                                        ^                                    |
                                        +------ 점수 미달 시 최대 2회 재실행 -----+

Domain은 문서 유형(주택/상가 임대차, 보험, 대출 등)을 1회 판별해 Analysis의
모든 조항 판정에 주입한다 — 같은 문언도 유형 따라 판정이 갈리기 때문
(docs/risk_taxonomy_v2.md §C).
"""

from langgraph.graph import END, StateGraph

from src.masking import mask_pii, masking_notice
from src.nodes.analysis import analysis_node
from src.nodes.domain import domain_node
from src.nodes.judge import judge_node
from src.nodes.parser import parser_node
from src.nodes.persona import persona_node
from src.state import (
    FAITHFULNESS_MIN,
    JUDGE_THRESHOLD,
    MAX_RETRIES,
    PipelineState,
    failing_aspects,
    judge_score_avg,
    shortcut_eligible,
)


def _increment_retry(state: PipelineState) -> dict:
    """재실행 직전 retry_count 증가용 보조 노드."""
    new_count = state["retry_count"] + 1
    print(f"[Retry] Judge 평균 점수 미달 ({JUDGE_THRESHOLD}점 기준) -> {new_count}차 재시도")
    return {"retry_count": new_count}


def _route_retry_target(state: PipelineState) -> str:
    """재생성 대상 분기 (자문 §3, #75): 미달 원인에 맞는 단계로만 돌아간다.

    - clarity만 미달 & risk_coverage·faithfulness가 임계값보다 확실히 위
      (shortcut_eligible) -> persona만 재실행 (판정 유효, 표현만 교정 —
      비용 절감. temperature=0이라 피드백 없이는 동일 결과가 나올 수 있지만,
      risk_coverage·faithfulness를 안전하게 재검증하지 않는 것 자체가
      #35가 드러낸 위험이었으므로 이번 PR은 그 안전장치만 다룬다)
    - 그 외(다른 aspect도 미달이거나, risk_coverage·faithfulness가 아슬아슬한
      경우) -> analysis부터 재실행. #35가 실측으로 드러낸 구멍(아슬아슬한
      통과를 재검증 없이 믿어 오분류가 새어나감)을 막기 위한 마진 조건.

    Judge rationale을 재생성 프롬프트에 주입하는 부분은 이번 PR에서 제외했다
    — 측정 결과 FP가 오히려 늘어(데모 contract_05 FP 1→5~6, 2회 일관) 별도
    이슈에서 문구를 다시 설계하기로 했다.
    """
    scores = state["judge_scores"]
    failing = set(failing_aspects(scores))
    if failing == {"clarity"} and shortcut_eligible(scores):
        print("[Retry] clarity만 미달 + risk_coverage/faithfulness 여유 확보 -> persona만 재실행")
        return "persona"
    return "analysis"


def _route_after_judge(state: PipelineState) -> str:
    """Judge 점수 기준 분기.

    - 평균 >= 임계값        -> 종료 (통과)
    - 미달 & 재시도 여유 있음 -> analysis 재실행
    - 미달 & 재시도 소진     -> needs_review 플래그 세우고 종료
    """
    avg = judge_score_avg(state["judge_scores"])
    faith = state["judge_scores"]["faithfulness"]

    # 필수 조건 (자문 §5): faithfulness 미달이면 평균과 무관하게 실패 처리 —
    # 원문 왜곡·창작 근거는 다른 항목 점수로 상쇄될 수 없는 치명 결함.
    if faith < FAITHFULNESS_MIN:
        if state["retry_count"] < MAX_RETRIES:
            print(f"[Judge] faithfulness {faith:.1f}점 < 필수 {FAITHFULNESS_MIN}점 -> 평균({avg:.2f}) 무관 재시도")
            return "retry"
        print(f"[Judge] faithfulness {faith:.1f}점 < 필수 {FAITHFULNESS_MIN}점, 재시도 소진 -> 주의 필요 플래그")
        return "flag"

    if avg >= JUDGE_THRESHOLD:
        print(f"[Judge] 평균 {avg:.2f}점 >= {JUDGE_THRESHOLD}점 -> 통과")
        return "pass"
    if state["retry_count"] < MAX_RETRIES:
        print(f"[Judge] 평균 {avg:.2f}점 < {JUDGE_THRESHOLD}점 (재시도 {state['retry_count']}/{MAX_RETRIES})")
        return "retry"
    print(f"[Judge] 평균 {avg:.2f}점 < {JUDGE_THRESHOLD}점, 재시도 소진 ({MAX_RETRIES}/{MAX_RETRIES}) -> 주의 필요 플래그")
    return "flag"


def _flag_needs_review(state: PipelineState) -> dict:
    """재시도 소진: '주의 필요' 플래그와 함께 결과 반환."""
    return {"needs_review": True}


def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("parser", parser_node)
    graph.add_node("domain", domain_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("persona", persona_node)
    graph.add_node("judge", judge_node)
    graph.add_node("increment_retry", _increment_retry)
    graph.add_node("flag_review", _flag_needs_review)

    graph.set_entry_point("parser")
    graph.add_edge("parser", "domain")
    graph.add_edge("domain", "analysis")
    graph.add_edge("analysis", "persona")
    graph.add_edge("persona", "judge")

    graph.add_conditional_edges(
        "judge",
        _route_after_judge,
        {
            "pass": END,
            "retry": "increment_retry",
            "flag": "flag_review",
        },
    )
    graph.add_conditional_edges(  # 재생성 대상 분기 (#75) — 미달 원인별로 analysis/persona만
        "increment_retry",
        _route_retry_target,
        {"analysis": "analysis", "persona": "persona"},
    )
    graph.add_edge("flag_review", END)

    return graph.compile()


# FastAPI 등에서 import 해서 쓰는 컴파일된 앱
pipeline = build_graph()


def run_pipeline(
    raw_text: str, persona: str = "adult", language: str = "ko", domain: str = ""
) -> PipelineState:
    """파이프라인 1회 실행 헬퍼.

    개인정보 마스킹은 Parser 이전에 1회 수행 — 이후 모든 단계(화면 표시 원문,
    LLM 입력, 인용 검사)가 동일한 마스킹 텍스트를 보므로 정합성이 유지된다.
    domain은 사용자가 업로드 시 선택한 문서 유형(없으면 빈 값 — Domain 노드가
    자동 판별을 시도하거나 "알 수 없음"으로 폴백).
    """
    raw_text, pii_counts = mask_pii(raw_text)
    initial_warnings = [masking_notice(pii_counts)] if pii_counts else []

    initial_state: PipelineState = {
        "raw_text": raw_text,
        "persona": persona,  # type: ignore[typeddict-item]
        "language": language or "ko",
        "domain": domain,
        "domain_evidence": "",
        "parse_warnings": initial_warnings,
        "clauses": [],
        "analysis_results": [],
        "adapted_results": [],
        "translations": {},
        "judge_scores": {  # type: ignore[typeddict-item]
            "clarity": 0.0,
            "faithfulness": 0.0,
            "risk_coverage": 0.0,
            "actionability": 0.0,
        },
        "retry_count": 0,
        "needs_review": False,
    }
    return pipeline.invoke(initial_state)  # type: ignore[return-value]
