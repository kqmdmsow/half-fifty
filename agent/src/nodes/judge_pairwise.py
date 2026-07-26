"""Pairwise Judge: 두 파이프라인 출력(A/B) 중 어느 쪽이 더 나은지 aspect별로 비교.

docs/human_llm_judge_agreement_design.md 11절(비교/선호 판단 기반 재설계) 전용 —
런타임 파이프라인(judge.py, 절대 5점 채점 + 재시도 게이팅)과는 별개로, 사람-LLM
선호 일치도 실험에서 오프라인으로만 호출한다.
"""

import json
from pathlib import Path
from typing import Literal, TypedDict

from src.llm import get_judge_llm, invoke_json
from src.state import AnalysisResult, Clause

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "judge_pairwise_rubric.txt"
_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

_ASPECTS = ["clarity", "faithfulness", "risk_coverage", "actionability"]

Winner = Literal["A", "B", "tie"]


class PairwiseVerdict(TypedDict):
    winner: Winner
    rationale: str


def compare(
    original_clauses: list[Clause],
    persona: str,
    output_a: list[AnalysisResult],
    output_b: list[AnalysisResult],
) -> dict[str, PairwiseVerdict]:
    """A/B 위치는 호출자가 미리 정한 그대로 판단한다 (위치 편향 통제는 compare_debiased 사용)."""
    clauses_text = "\n".join(f"[{c['clause_id']}] {c['text']}" for c in original_clauses)
    a_text = json.dumps(output_a, ensure_ascii=False, indent=2)
    b_text = json.dumps(output_b, ensure_ascii=False, indent=2)

    prompt = (
        _PROMPT_TEMPLATE.replace("{persona}", persona)
        .replace("{original_clauses}", clauses_text)
        .replace("{output_a}", a_text)
        .replace("{output_b}", b_text)
    )

    data = invoke_json(get_judge_llm(), prompt)
    return {
        aspect: PairwiseVerdict(winner=data[aspect]["winner"], rationale=data[aspect]["rationale"])
        for aspect in _ASPECTS
    }


def compare_debiased(
    original_clauses: list[Clause],
    persona: str,
    output_a: list[AnalysisResult],
    output_b: list[AnalysisResult],
) -> dict:
    """같은 쌍을 A/B 위치를 뒤집어 2회 호출 -> 위치 편향(position bias) 여부를 확인하고
    최종 승자를 결정한다. 정방향/역방향 판단이 일치하면 그 결과를 채택하고,
    불일치하면 "tie"로 처리하며 position_bias_suspected=True로 플래그한다.

    반환값의 "final"이 11.5절 지표(선호 일치율, Cohen's kappa) 계산에 쓰인다.
    """
    forward = compare(original_clauses, persona, output_a, output_b)
    backward_raw = compare(original_clauses, persona, output_b, output_a)

    flip = {"A": "B", "B": "A", "tie": "tie"}
    backward = {
        aspect: PairwiseVerdict(winner=flip[v["winner"]], rationale=v["rationale"])
        for aspect, v in backward_raw.items()
    }

    final = {}
    for aspect in _ASPECTS:
        w_fwd = forward[aspect]["winner"]
        w_bwd = backward[aspect]["winner"]
        if w_fwd == w_bwd:
            final[aspect] = {"winner": w_fwd, "position_bias_suspected": False}
        else:
            final[aspect] = {"winner": "tie", "position_bias_suspected": True}

    return {"forward": forward, "backward": backward, "final": final}
