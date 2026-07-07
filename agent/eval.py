"""파이프라인 자동 평가 스크립트.

data/의 계약서 5건을 전부 4단계 파이프라인(Parser -> Analysis -> Persona ->
Judge)에 실행하고, data/labels.md의 정답과 대조하여 문서별 위험 조항
리콜(찾은 위험 건수 / 정답 위험 건수)과 정상 문서 오탐(false positive)
건수를 측정한다. 문서별 실행 시간과 대략적 토큰 사용량도 함께 기록해
docs/eval_results_v2.md로 저장한다.

주의: 여기서 말하는 "리콜"은 조항 단위로 정확히 같은 조항인지까지 대조하는
것이 아니라, risk_level != "안전"으로 판정된 조항 개수를 정답 위험 건수와
비교하는 건수 기준 근사치다. Phase 2의 정식 Baseline vs Ours 비교 실험에서는
조항 단위 정답 매칭으로 정교화할 예정.

사용법:
    cd agent
    source .venv/bin/activate
    python eval.py
"""

import time
from pathlib import Path

from src.graph import run_pipeline
from src.llm import get_token_usage, reset_token_usage

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_PATH = Path(__file__).parent.parent / "docs" / "eval_results_v2.md"

# data/labels.md 기준 문서별 기대 위험 조항 수
EXPECTED_RISK_COUNTS = {
    "sample_lease_contract.txt": 4,
    "contract_02_finance_loan.txt": 6,
    "contract_03_lease_normal.txt": 0,
    "contract_04_gym_membership.txt": 4,
    "contract_05_molit_standard.txt": 0,
}


def evaluate_file(filename: str, expected_risk: int) -> dict:
    text = (DATA_DIR / filename).read_text(encoding="utf-8")

    reset_token_usage()
    start = time.perf_counter()
    result = run_pipeline(text, persona="adult")
    elapsed = time.perf_counter() - start
    tokens = get_token_usage()

    found_risk = sum(1 for r in result["adapted_results"] if r["risk_level"] != "안전")

    if expected_risk == 0:
        recall_display = "-"
        false_positive = found_risk
    else:
        recall_display = f"{min(found_risk, expected_risk)}/{expected_risk}"
        false_positive = max(found_risk - expected_risk, 0)

    return {
        "file": filename,
        "clause_count": len(result["clauses"]),
        "recall_display": recall_display,
        "false_positive": false_positive,
        "elapsed": elapsed,
        "input_tokens": tokens["input_tokens"],
        "output_tokens": tokens["output_tokens"],
        "judge_scores": result["judge_scores"],
        "retry_count": result["retry_count"],
        "needs_review": result["needs_review"],
    }


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
        avg = sum(r["judge_scores"].values()) / len(r["judge_scores"])
        lines.append(
            f"| {r['file']} | {r['clause_count']} | {r['recall_display']} | "
            f"{r['false_positive']} | {r['elapsed']:.1f} | "
            f"{r['input_tokens']}/{r['output_tokens']} | {avg:.2f} | "
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


def main() -> None:
    rows = [evaluate_file(f, expected) for f, expected in EXPECTED_RISK_COUNTS.items()]
    markdown = render_markdown(rows)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
