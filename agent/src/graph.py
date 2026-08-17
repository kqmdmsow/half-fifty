"""LangGraph 4단계 파이프라인 조립 (착수보고서 <그림 3>).

Parser(Module) -> Analysis(Agent) -> Persona(Agent) -> Judge(Agent)
                      ^                                    |
                      +---- 점수 미달 시 최대 2회 재실행 ----+
"""

from langgraph.graph import END, StateGraph

from src.masking import mask_pii, masking_notice
from src.nodes.analysis import analysis_node
from src.nodes.judge import judge_node
from src.nodes.parser import parser_node
from src.nodes.persona import persona_node
from src.state import FAITHFULNESS_MIN, JUDGE_THRESHOLD, MAX_RETRIES, PipelineState, judge_score_avg


def _increment_retry(state: PipelineState) -> dict:
    """재실행 직전 retry_count 증가용 보조 노드."""
    new_count = state["retry_count"] + 1
    print(f"[Retry] Judge 평균 점수 미달 ({JUDGE_THRESHOLD}점 기준) -> {new_count}차 재시도")
    return {"retry_count": new_count}


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
    graph.add_node("analysis", analysis_node)
    graph.add_node("persona", persona_node)
    graph.add_node("judge", judge_node)
    graph.add_node("increment_retry", _increment_retry)
    graph.add_node("flag_review", _flag_needs_review)

    graph.set_entry_point("parser")
    graph.add_edge("parser", "analysis")
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
    graph.add_edge("increment_retry", "analysis")  # 재생성 루프
    graph.add_edge("flag_review", END)

    return graph.compile()


# FastAPI 등에서 import 해서 쓰는 컴파일된 앱
pipeline = build_graph()


def run_pipeline(raw_text: str, persona: str = "adult") -> PipelineState:
    """파이프라인 1회 실행 헬퍼.

    개인정보 마스킹은 Parser 이전에 1회 수행 — 이후 모든 단계(화면 표시 원문,
    LLM 입력, 인용 검사)가 동일한 마스킹 텍스트를 보므로 정합성이 유지된다.
    """
    raw_text, pii_counts = mask_pii(raw_text)
    initial_warnings = [masking_notice(pii_counts)] if pii_counts else []

    initial_state: PipelineState = {
        "raw_text": raw_text,
        "persona": persona,  # type: ignore[typeddict-item]
        "parse_warnings": initial_warnings,
        "clauses": [],
        "analysis_results": [],
        "adapted_results": [],
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
