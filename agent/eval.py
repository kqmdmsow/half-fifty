"""파이프라인 자동 평가 스크립트.

data/의 계약서 5건을 전부 4단계 파이프라인(Parser -> Analysis -> Persona ->
Judge, "Ours")에 실행하고, data/labels.md의 정답과 대조하여 문서별 위험 조항
리콜(찾은 위험 건수 / 정답 위험 건수)과 정상 문서 오탐(false positive)
건수를 측정한다. 문서별 실행 시간과 대략적 토큰 사용량도 함께 기록해
docs/eval_results_v2.md로 저장한다.

같은 5건을 단일 LLM 호출 Baseline(src/baseline.py, 착수보고서 <표 6>)으로도
실행해 Ours와 나란히 비교한 결과를 docs/eval_baseline_vs_ours.md로 저장한다.
Judge는 두 경로 모두 동일한 judge_node를 사용해 같은 기준으로 채점한다.

주의: 여기서 말하는 "리콜"은 조항 단위로 정확히 같은 조항인지까지 대조하는
것이 아니라, risk_level != "안전"으로 판정된 조항 개수를 정답 위험 건수와
비교하는 건수 기준 근사치다. 조항 단위 정답 매칭으로 정교화하는 건 이번
범위 밖이다.

사용법:
    cd agent
    source .venv/bin/activate
    python eval.py
"""

import time
from pathlib import Path
from typing import Callable

from src.baseline import run_baseline
from src.graph import run_pipeline
from src.llm import get_token_usage, reset_token_usage
from src.state import PipelineState

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_PATH = Path(__file__).parent.parent / "docs" / "eval_results_v2.md"
COMPARISON_OUT_PATH = Path(__file__).parent.parent / "docs" / "eval_baseline_vs_ours.md"

# data/labels.md 기준 문서별 기대 위험 조항 수
EXPECTED_RISK_COUNTS = {
    "sample_lease_contract.txt": 4,
    "contract_02_finance_loan.txt": 6,
    "contract_03_lease_normal.txt": 0,
    "contract_04_gym_membership.txt": 4,
    "contract_05_molit_standard.txt": 0,
}

Runner = Callable[..., PipelineState]


def _measure(runner: Runner, filename: str, expected_risk: int) -> dict:
    text = (DATA_DIR / filename).read_text(encoding="utf-8")

    reset_token_usage()
    start = time.perf_counter()
    result = runner(text, persona="adult")
    elapsed = time.perf_counter() - start
    tokens = get_token_usage()

    found_risk = sum(1 for r in result["adapted_results"] if r["risk_level"] != "안전")

    if expected_risk == 0:
        recall_display = "-"
        false_positive = found_risk
    else:
        recall_display = f"{min(found_risk, expected_risk)}/{expected_risk}"
        false_positive = max(found_risk - expected_risk, 0)

    judge_avg = sum(result["judge_scores"].values()) / len(result["judge_scores"])

    return {
        "file": filename,
        "clause_count": len(result["clauses"]),
        "recall_display": recall_display,
        "false_positive": false_positive,
        "elapsed": elapsed,
        "input_tokens": tokens["input_tokens"],
        "output_tokens": tokens["output_tokens"],
        "judge_scores": result["judge_scores"],
        "judge_avg": judge_avg,
        "retry_count": result["retry_count"],
        "needs_review": result["needs_review"],
    }


def evaluate_file(filename: str, expected_risk: int) -> dict:
    return _measure(run_pipeline, filename, expected_risk)


def evaluate_file_baseline(filename: str, expected_risk: int) -> dict:
    return _measure(run_baseline, filename, expected_risk)


def render_markdown(rows: list) -> str:
    total_elapsed = sum(r["elapsed"] for r in rows)
    total_input = sum(r["input_tokens"] for r in rows)
    total_output = sum(r["output_tokens"] for r in rows)

    lines = [
        "# 평가 결과 (Parser v2 + Prompt v2)",
        "",
        "`agent/eval.py`로 `data/`의 계약서 5건을 파이프라인에 실행하고 "
        "`data/labels.md` 정답과 대조한 결과.",
        "",
        "| 문서 | 조항 수 | 위험 리콜(찾음/정답) | 오탐(FP) | 실행시간(초) | "
        "토큰(입력/출력) | Judge 평균 | 재시도 | 주의필요 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['file']} | {r['clause_count']} | {r['recall_display']} | "
            f"{r['false_positive']} | {r['elapsed']:.1f} | "
            f"{r['input_tokens']}/{r['output_tokens']} | {r['judge_avg']:.2f} | "
            f"{r['retry_count']} | {r['needs_review']} |"
        )

    lines += [
        "",
        f"**합계**: 실행시간 {total_elapsed:.1f}초, 토큰 {total_input}/{total_output} (입력/출력)",
        "",
        "리콜은 조항 단위 정답 매칭이 아니라 문서별 위험 판정 건수 대 정답 건수의 "
        "근사치다 (자세한 내용은 eval.py 상단 주석 참고).",
    ]
    return "\n".join(lines) + "\n"


def render_comparison_markdown(ours_rows: list, baseline_rows: list) -> str:
    lines = [
        "# Baseline vs Ours 비교",
        "",
        "착수보고서 <표 6> 성능 검증 시나리오: 단일 LLM 호출(Baseline, 페르소나 적응·"
        "재생성 없음) vs 4단계 파이프라인(Ours). 같은 모델(MODEL_WORKER)과 같은 Judge "
        "기준(judge_node)으로 채점해 파이프라인 구조 차이만 비교한다.",
        "",
        "| 문서 | Judge 평균 (Ours/Base) | 위험 리콜 (Ours/Base) | 오탐 FP (Ours/Base) | "
        "실행시간초 (Ours/Base) | 토큰 (Ours/Base) |",
        "|---|---|---|---|---|---|",
    ]
    for o, b in zip(ours_rows, baseline_rows):
        lines.append(
            f"| {o['file']} | {o['judge_avg']:.2f} / {b['judge_avg']:.2f} | "
            f"{o['recall_display']} / {b['recall_display']} | "
            f"{o['false_positive']} / {b['false_positive']} | "
            f"{o['elapsed']:.1f} / {b['elapsed']:.1f} | "
            f"{o['input_tokens']}+{o['output_tokens']} / {b['input_tokens']}+{b['output_tokens']} |"
        )

    lines += [
        "",
        "## Judge 4 Aspect 상세 (Ours/Base)",
        "",
        "| 문서 | clarity | faithfulness | risk_coverage | actionability |",
        "|---|---|---|---|---|",
    ]
    for o, b in zip(ours_rows, baseline_rows):
        cells = []
        for aspect in ("clarity", "faithfulness", "risk_coverage", "actionability"):
            cells.append(f"{o['judge_scores'][aspect]:.1f}/{b['judge_scores'][aspect]:.1f}")
        lines.append(f"| {o['file']} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "리콜/오탐 기준은 eval.py 상단 주석과 동일한 건수 기준 근사치다.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ours_rows = [evaluate_file(f, expected) for f, expected in EXPECTED_RISK_COUNTS.items()]
    markdown = render_markdown(ours_rows)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"저장 완료: {OUT_PATH}")

    baseline_rows = [
        evaluate_file_baseline(f, expected) for f, expected in EXPECTED_RISK_COUNTS.items()
    ]
    comparison_markdown = render_comparison_markdown(ours_rows, baseline_rows)
    COMPARISON_OUT_PATH.write_text(comparison_markdown, encoding="utf-8")
    print(comparison_markdown)
    print(f"저장 완료: {COMPARISON_OUT_PATH}")


if __name__ == "__main__":
    main()
