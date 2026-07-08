"""Judge Agent: LLM-as-a-Judge 정량 평가.

4 Aspect x 5점 Rubric (착수보고서 <표 5>):
- Clarity        : 설명이 페르소나 난이도에 적합한가
- Faithfulness   : 원문에 없는 내용을 추가하지 않았는가 (환각)
- Risk Coverage  : 위험 조항을 누락 없이 식별했는가
- Actionability  : 실행 가능한 행동(질문)을 제시하는가

src/prompts/judge_rubric.txt로 MODEL_JUDGE를 호출해 채점한다.
점수 근거(rationale)는 사람-LLM 상관도 분석 참고용으로 콘솔에 로그로 남긴다.
"""

import json
from pathlib import Path

from src.llm import get_judge_llm, invoke_json
from src.state import JudgeScores, PipelineState

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "judge_rubric.txt"
_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

_ASPECTS = ["clarity", "faithfulness", "risk_coverage", "actionability"]


def _judge(state: PipelineState) -> JudgeScores:
    original_clauses = "\n".join(
        f"[{c['clause_id']}] {c['text']}" for c in state["clauses"]
    )
    final_output = json.dumps(state["adapted_results"], ensure_ascii=False, indent=2)

    prompt = (
        _PROMPT_TEMPLATE.replace("{persona}", state["persona"])
        .replace("{original_clauses}", original_clauses)
        .replace("{final_output}", final_output)
    )

    data = invoke_json(get_judge_llm(), prompt)

    scores = {}
    for aspect in _ASPECTS:
        aspect_data = data[aspect]
        scores[aspect] = float(aspect_data["score"])
        print(f"[Judge] {aspect}: {aspect_data['score']}점 — {aspect_data['rationale']}")

    return JudgeScores(
        clarity=scores["clarity"],
        faithfulness=scores["faithfulness"],
        risk_coverage=scores["risk_coverage"],
        actionability=scores["actionability"],
    )


def judge_node(state: PipelineState) -> dict:
    """LangGraph 노드: adapted_results -> judge_scores."""
    scores = _judge(state)
    return {"judge_scores": scores}
