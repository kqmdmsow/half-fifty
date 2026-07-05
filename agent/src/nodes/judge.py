"""Judge Agent: LLM-as-a-Judge 정량 평가.

4 Aspect x 5점 Rubric (착수보고서 <표 5>):
- Clarity        : 설명이 페르소나 난이도에 적합한가
- Faithfulness   : 원문에 없는 내용을 추가하지 않았는가 (환각)
- Risk Coverage  : 위험 조항을 누락 없이 식별했는가
- Actionability  : 실행 가능한 행동(질문)을 제시하는가

현재는 더미 구현(고정 점수). LLM 연동 시 src/prompts/judge_rubric.txt 사용.
점수 근거(rationale)도 함께 출력하게 만들 것 — 사람-LLM 상관도 분석 때 필요.
"""

from pathlib import Path

from src.state import JudgeScores, PipelineState

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "judge_rubric.txt"


def _judge_dummy(state: PipelineState) -> JudgeScores:
    """더미 채점: 파이프라인 흐름 검증용 고정 점수.

    재생성 루프를 눈으로 확인하고 싶으면 아래 점수를 3.0 등으로 낮춰서
    graph.py 의 조건부 엣지가 analysis 로 되돌아가는지 테스트해 볼 것.
    """
    return JudgeScores(
        clarity=4.0,
        faithfulness=4.0,
        risk_coverage=4.0,
        actionability=4.0,
    )


def judge_node(state: PipelineState) -> dict:
    """LangGraph 노드: adapted_results -> judge_scores.

    TODO(민제): LLM 연동 시 원본 조항 + 최종 출력을 함께 넣어 Rubric 채점.
    """
    scores = _judge_dummy(state)
    return {"judge_scores": scores}
