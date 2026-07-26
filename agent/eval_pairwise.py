"""정답앵커 쌍(data/anchor_pairs.json) 기반 LLM Judge 선호 판단 검증 스크립트.

docs/human_llm_judge_agreement_design.md 11절(비교/선호 판단 기반 재설계)의
RQ6("LLM Judge의 선호 판단은 골든데이터 정답과 얼마나 일치하는가?")를 직접
검증한다. 각 앵커 쌍은 같은 조항에 대한 정답형 출력(correct_output)과
의도적 오답형 출력(wrong_output)으로 구성되어 있고, LLM에게는 어느 쪽이
correct인지 알려주지 않은 채 A/B 중 어느 쪽이 나은지 aspect별로 판단하게 한다.

judge_pairwise.compare_debiased()가 이미 위치 편향 통제(A/B 뒤집어 2회 호출)를
하므로, 여기서는 항상 output_a=correct_output, output_b=wrong_output으로
고정해서 호출한다 — final.winner == "A"면 LLM이 정답을 선호한 것이다.

사용법:
    cd agent
    source .venv/bin/activate
    python eval_pairwise.py
"""

import json
from pathlib import Path

from src.nodes.judge_pairwise import _ASPECTS, compare_debiased

ANCHOR_PAIRS_PATH = Path(__file__).parent.parent / "data" / "anchor_pairs.json"
OUT_PATH = Path(__file__).parent.parent / "docs" / "eval_pairwise_anchor_report.md"


def _load_anchor_pairs() -> list:
    with open(ANCHOR_PAIRS_PATH, encoding="utf-8") as f:
        return json.load(f)


def run_anchor_pairs() -> list:
    """모든 앵커 쌍에 대해 compare_debiased()를 호출하고 결과를 모은다."""
    pairs = _load_anchor_pairs()
    results = []
    for pair in pairs:
        verdict = compare_debiased(
            original_clauses=[pair["clause"]],
            persona="adult",
            output_a=[pair["correct_output"]],
            output_b=[pair["wrong_output"]],
        )
        results.append({"pair": pair, "verdict": verdict})
        print(f"[{pair['id']}] " + ", ".join(f"{a}={verdict['final'][a]['winner']}" for a in _ASPECTS))
    return results


def render_report(results: list) -> str:
    """RQ6: aspect별 정답 일치율(Accuracy vs Ground Truth) 집계."""
    lines = [
        "# 정답앵커 쌍 — LLM Judge 선호 판단 검증 결과 (RQ6)",
        "",
        "`data/anchor_pairs.json`(10건, 위험 5/안전 5)에 대해 `judge_pairwise.compare_debiased()`를 "
        "호출한 결과. A=정답형 출력, B=오답형 출력으로 고정 — winner=A면 LLM이 정답을 선호한 것.",
        "",
        "## 쌍별 상세",
        "",
        "| id | 정답 risk_level | " + " | ".join(_ASPECTS) + " | 위치편향 의심 |",
        "|---|---|" + "---|" * len(_ASPECTS) + "---|",
    ]

    aspect_correct = {a: 0 for a in _ASPECTS}
    aspect_total = {a: 0 for a in _ASPECTS}
    bias_suspected_count = 0

    for r in results:
        pair = r["pair"]
        final = r["verdict"]["final"]
        winners = []
        any_bias = False
        for a in _ASPECTS:
            w = final[a]["winner"]
            winners.append(w)
            if final[a]["position_bias_suspected"]:
                any_bias = True
            if w != "tie":
                aspect_total[a] += 1
                if w == "A":
                    aspect_correct[a] += 1
        if any_bias:
            bias_suspected_count += 1
        lines.append(
            f"| {pair['id']} | {pair['gold_risk_level']} | " + " | ".join(winners) +
            f" | {'예' if any_bias else '-'} |"
        )

    lines += [
        "",
        "## Aspect별 정답 일치율 (Accuracy vs Ground Truth)",
        "",
        "| aspect | 정답 선호 / 판단 건수 (tie 제외) | 정답 일치율 |",
        "|---|---|---|",
    ]
    for a in _ASPECTS:
        total = aspect_total[a]
        correct = aspect_correct[a]
        rate = f"{correct/total:.0%}" if total else "-"
        lines.append(f"| {a} | {correct}/{total} | {rate} |")

    lines += [
        "",
        f"위치 편향 의심(정방향/역방향 판단 불일치)이 발생한 쌍: {bias_suspected_count}/{len(results)}건",
        "",
        "**해석 기준**: risk_coverage·faithfulness는 사실 판단이라 정답 일치율이 낮으면 "
        "LLM Judge를 곧이곧대로 신뢰할 수 없다는 직접 증거다 (RQ6). clarity는 문체 판단이라 "
        "상대적으로 덜 걱정할 항목이다.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    results = run_anchor_pairs()
    report = render_report(results)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
