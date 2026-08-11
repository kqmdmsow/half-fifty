"""LangGraph 4단계 파이프라인 조립 (착수보고서 <그림 3>).

Parser(Module) -> Analysis(Agent) -> Persona(Agent) -> Judge(Agent)
                      ^                                    |
                      +---- 점수 미달 시 최대 2회 재실행 ----+
"""

from langgraph.graph import END, StateGraph

from src.nodes.analysis import analysis_node
from src.nodes.judge import judge_node
from src.nodes.parser import parser_node
from src.nodes.persona import persona_node
from src.state import FAITHFULNESS_MIN, JUDGE_THRESHOLD, MAX_RETRIES, PipelineState, judge_score_avg


def _failing_aspects(scores) -> list[str]:
    """임계 미달 aspect 목록 (JUDGE_ASPECT_KEYS 순서 유지)."""
    from src.state import JUDGE_ASPECT_KEYS

    return [k for k in JUDGE_ASPECT_KEYS if scores[k] < JUDGE_THRESHOLD]


def _format_feedback(scores) -> str:
    """미달 aspect의 점수·채점 근거를 재생성 프롬프트 주입용 텍스트로 정리."""
    rationale = scores.get("rationale") or {}
    lines = [
        f"- {k} {scores[k]:.0f}점: {rationale.get(k, '근거 미기록')}"
        for k in _failing_aspects(scores)
    ]
    return "\n".join(lines)


def _increment_retry(state: PipelineState) -> dict:
    """재실행 직전 retry_count 증가 + 채점 피드백 구성 (재생성 프롬프트 주입용).

    자문 §3 반영: 동일 프롬프트 단순 반복은 "우연히 다른 답"을 기대하는
    구조 — 무엇이 미달이었는지를 다음 시도에 전달해야 재생성이 개선이 된다.
    """
    new_count = state["retry_count"] + 1
    feedback = _format_feedback(state["judge_scores"])
    print(f"[Retry] Judge 미달 -> {new_count}차 재시도. 피드백:\n{feedback}")
    return {"retry_count": new_count, "judge_feedback": feedback}


def _route_retry_target(state: PipelineState) -> str:
    """재생성 대상 분기 (자문 §3): 미달 원인에 맞는 단계로만 돌아간다.

    - faithfulness(왜곡)·risk_coverage(누락)·actionability(질문 품질)는
      Analysis 산출물의 문제 → analysis부터 재실행
    - clarity(눈높이)만 미달이면 판정은 유효하고 표현만 문제 → persona만 재실행
    """
    failing = _failing_aspects(state["judge_scores"])
    if failing and set(failing) <= {"clarity"}:
        print("[Retry] clarity만 미달 -> persona만 재실행")
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
    graph.add_conditional_edges(  # 재생성 루프: 미달 원인별 대상 분기 (자문 §3)
        "increment_retry",
        _route_retry_target,
        {"analysis": "analysis", "persona": "persona"},
    )
    graph.add_edge("flag_review", END)

    return graph.compile()


# FastAPI 등에서 import 해서 쓰는 컴파일된 앱
pipeline = build_graph()


def run_pipeline(raw_text: str, persona: str = "adult") -> PipelineState:
    """파이프라인 1회 실행 헬퍼."""
    initial_state: PipelineState = {
        "raw_text": raw_text,
        "persona": persona,  # type: ignore[typeddict-item]
        "parse_warnings": [],
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
        "judge_feedback": "",
        "needs_review": False,
    }
    return pipeline.invoke(initial_state)  # type: ignore[return-value]
