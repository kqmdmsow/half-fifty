"""정답앵커 쌍(data/anchor_pairs.json) 기반 LLM Judge 선호 판단 검증 스크립트.

docs/human_llm_judge_agreement_design.md 11절(비교/선호 판단 기반 재설계)의
RQ6("LLM Judge의 선호 판단은 골든데이터 정답과 얼마나 일치하는가?")를 직접
검증한다. 각 앵커 쌍은 같은 조항에 대한 정답형 출력(correct_output)과
의도적 오답형 출력(wrong_output)으로 구성되어 있고, LLM에게는 어느 쪽이
correct인지 알려주지 않은 채 A/B 중 어느 쪽이 나은지 aspect별로 판단하게 한다.

judge_pairwise.compare_debiased()가 이미 위치 편향 통제(A/B 뒤집어 2회 호출)를
하므로, 여기서는 항상 output_a=correct_output, output_b=wrong_output으로
고정해서 호출한다 — final.winner == "A"면 LLM이 정답을 선호한 것이다.

재현성 통제: 단발 채점은 반복 실행 시 ±0.1~0.6점 흔들림이 확인돼
(docs/reproducibility.md), 보고용 수치는 --repeats(기본 3)회 반복 후
aspect별 다수결(majority vote)로 확정한다. 과반이 없으면 tie 처리.

판사 패밀리 교차검증: worker(Claude)가 만든 출력을 같은 Claude 패밀리 judge가
채점하면 self-preference bias가 개입할 수 있으므로, --judge gemini로 다른
패밀리 판사에게 같은 쌍을 태워 교차검증한다. Gemini judge는 평가 전용이며
제품 파이프라인 모델(Claude 고정 정책)과 무관하다.
(gemini 사용 시 `pip install langchain-google-genai` + GOOGLE_API_KEY 필요 —
requirements.txt에는 넣지 않은 평가 전용 의존성)

출력 파일은 판사별로 분리한다(docs/eval_pairwise_anchor_<judge>.md) —
과거 기록(eval_pairwise_anchor_report.md, Gemini 시절 10쌍)은 덮어쓰지 않는다.

사용법:
    cd agent
    source .venv/bin/activate
    python eval_pairwise.py --judge claude              # 기본: repeats=3
    python eval_pairwise.py --judge gemini --repeats 3
"""

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path

from src.nodes.judge_pairwise import _ASPECTS, compare_debiased

ANCHOR_PAIRS_PATH = Path(__file__).parent.parent / "data" / "anchor_pairs.json"
DOCS_DIR = Path(__file__).parent.parent / "docs"

GEMINI_JUDGE_MODEL = "gemini-flash-lite-latest"

_MAX_RETRIES = 4
_RETRY_BASE_SLEEP = 15  # 초 — Gemini 무료 티어 분당 한도(429) 대응


def _get_judge_llm(judge: str, nim_model: str | None = None):
    if judge == "claude":
        from src.llm import get_judge_llm

        return get_judge_llm(), os.getenv("MODEL_JUDGE", "claude-sonnet-4-6")
    if judge == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = os.getenv("MODEL_JUDGE_GEMINI", GEMINI_JUDGE_MODEL)
        return ChatGoogleGenerativeAI(model=model, temperature=0), model
    if judge == "solar":
        # Upstage Solar(OpenAI 호환) — 한국어 특화 판사. UPSTAGE_API_KEY 필요.
        from langchain_openai import ChatOpenAI

        model = os.getenv("MODEL_JUDGE_SOLAR", "solar-pro3")
        return (
            ChatOpenAI(
                model=model,
                temperature=0,
                base_url="https://api.upstage.ai/v1",
                api_key=os.getenv("UPSTAGE_API_KEY"),
                max_retries=0,
            ),
            model,
        )
    if judge == "nim":
        # NVIDIA NIM(OpenAI 호환) — 무료 크레딧으로 제3·제4 판사 패밀리 확보용.
        # NVIDIA_API_KEY 필요, 모델은 --model로 지정 (예: moonshotai/kimi-k2.6)
        from langchain_openai import ChatOpenAI

        if not nim_model:
            raise ValueError("--judge nim에는 --model <NIM 모델 id>가 필요합니다")
        return (
            ChatOpenAI(
                model=nim_model,
                temperature=0,
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=os.getenv("NVIDIA_API_KEY"),
                max_retries=0,  # 재시도는 _compare_with_retry가 담당
            ),
            nim_model,
        )
    raise ValueError(f"지원하지 않는 judge: {judge}")


def _is_retryable(e: Exception) -> bool:
    """429·일시 장애만 재시도. 크레딧 소진/인증 오류(400·401 등)는 기다려도 해결 안 되므로
    즉시 중단해 체크포인트를 보존한다."""
    name = type(e).__name__
    if name in ("BadRequestError", "AuthenticationError", "PermissionDeniedError"):
        return False
    return True


def _compare_with_retry(pair: dict, llm) -> dict:
    for attempt in range(_MAX_RETRIES):
        try:
            return compare_debiased(
                original_clauses=[pair["clause"]],
                persona="adult",
                output_a=[pair["correct_output"]],
                output_b=[pair["wrong_output"]],
                llm=llm,
            )
        except Exception as e:  # 429/일시 오류 — 지수 백오프 후 재시도
            if not _is_retryable(e) or attempt == _MAX_RETRIES - 1:
                raise
            sleep_s = _RETRY_BASE_SLEEP * (2**attempt)
            print(f"  [재시도 {attempt + 1}/{_MAX_RETRIES - 1}] {type(e).__name__}: {e} — {sleep_s}s 대기")
            time.sleep(sleep_s)


def _majority(winners: list[str]) -> tuple[str, bool]:
    """반복 판정의 다수결. 과반 승자가 없으면 tie. (winner, unstable) 반환."""
    counts = Counter(winners)
    winner, top = counts.most_common(1)[0]
    if top * 2 <= len(winners):  # 과반 미달
        return "tie", True
    return winner, len(counts) > 1


def run_anchor_pairs(llm, repeats: int, checkpoint_path: Path) -> list:
    """모든 앵커 쌍에 대해 compare_debiased()를 repeats회 호출하고 다수결로 확정한다.

    쌍 1건이 끝날 때마다 checkpoint(JSONL)에 append — API 크레딧 소진 등으로 중단돼도
    완료분은 보존되고, 재실행하면 체크포인트에 있는 쌍은 건너뛰고 이어서 돈다.
    (2026-08-05 Claude 크레딧 소진으로 12/44 진행분을 통째로 유실한 사고 재발 방지)
    """
    done: dict[str, dict] = {}
    if checkpoint_path.exists():
        with open(checkpoint_path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                done[rec["id"]] = rec
        print(f"체크포인트에서 {len(done)}건 로드 ({checkpoint_path.name}) — 해당 쌍은 건너뜀")

    pairs = _load_anchor_pairs()
    results = []
    with open(checkpoint_path, "a", encoding="utf-8") as ckpt:
        for i, pair in enumerate(pairs, 1):
            if pair["id"] in done:
                results.append({"pair": pair, "final": done[pair["id"]]["final"]})
                continue
            runs = [_compare_with_retry(pair, llm) for _ in range(repeats)]
            final = {}
            for a in _ASPECTS:
                votes = [r["final"][a]["winner"] for r in runs]
                winner, unstable = _majority(votes)
                final[a] = {
                    "winner": winner,
                    "votes": votes,
                    "unstable": unstable,
                    "position_bias_runs": sum(r["final"][a]["position_bias_suspected"] for r in runs),
                }
            results.append({"pair": pair, "final": final})
            ckpt.write(json.dumps({"id": pair["id"], "final": final}, ensure_ascii=False) + "\n")
            ckpt.flush()
            print(
                f"[{i}/{len(pairs)}] {pair['id']}: "
                + ", ".join(f"{a}={final[a]['winner']}({'/'.join(final[a]['votes'])})" for a in _ASPECTS)
            )
    return results


def _load_anchor_pairs() -> list:
    with open(ANCHOR_PAIRS_PATH, encoding="utf-8") as f:
        return json.load(f)


def render_report(results: list, judge: str, model_name: str, repeats: int) -> str:
    """RQ6: aspect별 정답 일치율(Accuracy vs Ground Truth) 집계."""
    n_risk = sum(1 for r in results if r["pair"]["gold_risk_level"] == "위험")
    n_safe = len(results) - n_risk
    lines = [
        f"# 정답앵커 쌍 — LLM Judge 선호 판단 검증 결과 (RQ6, judge={judge})",
        "",
        f"`data/anchor_pairs.json`({len(results)}건, 위험 {n_risk}/안전 {n_safe})에 대해 "
        "`judge_pairwise.compare_debiased()`를 호출한 결과. A=정답형 출력, B=오답형 출력으로 "
        "고정 — winner=A면 LLM이 정답을 선호한 것.",
        "",
        f"> **실행 조건**: judge 모델 `{model_name}`, 쌍마다 debiased 비교(정/역방향 2회 호출)를 "
        f"**{repeats}회 반복** 후 aspect별 다수결로 확정(과반 없으면 tie). "
        "반복 간 판정이 갈린 aspect는 '불안정' 컬럼에 표시 — 단발 채점의 재현성 문제 "
        "(docs/reproducibility.md) 통제 목적.",
        "",
        "## 쌍별 상세 (다수결 확정 결과)",
        "",
        "| id | 정답 risk_level | " + " | ".join(_ASPECTS) + " | 불안정 | 위치편향 감지 횟수 |",
        "|---|---|" + "---|" * len(_ASPECTS) + "---|---|",
    ]

    aspect_correct = {a: 0 for a in _ASPECTS}
    aspect_total = {a: 0 for a in _ASPECTS}
    aspect_unstable = {a: 0 for a in _ASPECTS}
    bias_run_total = 0

    for r in results:
        pair = r["pair"]
        final = r["final"]
        winners, unstable_aspects = [], []
        bias_runs = 0
        for a in _ASPECTS:
            w = final[a]["winner"]
            winners.append(w)
            if final[a]["unstable"]:
                unstable_aspects.append(a)
                aspect_unstable[a] += 1
            bias_runs += final[a]["position_bias_runs"]
            if w != "tie":
                aspect_total[a] += 1
                if w == "A":
                    aspect_correct[a] += 1
        bias_run_total += bias_runs
        lines.append(
            f"| {pair['id']} | {pair['gold_risk_level']} | " + " | ".join(winners)
            + f" | {', '.join(unstable_aspects) if unstable_aspects else '-'} | {bias_runs} |"
        )

    lines += [
        "",
        "## Aspect별 정답 일치율 (Accuracy vs Ground Truth)",
        "",
        "| aspect | 정답 선호 / 판단 건수 (tie 제외) | 정답 일치율 | 반복 간 불안정 쌍 수 |",
        "|---|---|---|---|",
    ]
    for a in _ASPECTS:
        total = aspect_total[a]
        correct = aspect_correct[a]
        rate = f"{correct/total:.0%}" if total else "-"
        lines.append(f"| {a} | {correct}/{total} | {rate} | {aspect_unstable[a]} |")

    total_decisions = len(results) * len(_ASPECTS) * repeats
    lines += [
        "",
        f"위치 편향 의심(정방향/역방향 판단 불일치) 발생: 전체 {total_decisions}회 "
        f"aspect-판정 중 {bias_run_total}회 ({bias_run_total/total_decisions:.0%})",
        "",
        "**해석 기준**: risk_coverage·faithfulness는 사실 판단이라 정답 일치율이 낮으면 "
        "LLM Judge를 곧이곧대로 신뢰할 수 없다는 직접 증거다 (RQ6). clarity는 문체 판단이라 "
        "상대적으로 덜 걱정할 항목이다. judge=claude 결과는 worker와 같은 패밀리라 "
        "self-preference bias 가능성이 있으므로, 반드시 judge=gemini 결과와 교차 대조할 것.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="정답앵커 쌍 pairwise judge 검증 (RQ6)")
    parser.add_argument("--judge", choices=["claude", "gemini", "solar", "nim"], default="claude")
    parser.add_argument("--model", help="--judge nim일 때 NIM 모델 id (예: moonshotai/kimi-k2.6)")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    llm, model_name = _get_judge_llm(args.judge, args.model)
    print(f"judge={args.judge} ({model_name}), repeats={args.repeats}")

    # nim은 모델별로 파일 분리 (moonshotai/kimi-k2.6 -> nim_kimi-k2.6)
    judge_slug = args.judge if args.judge != "nim" else "nim_" + model_name.split("/")[-1]
    checkpoint_path = DOCS_DIR / f"eval_pairwise_anchor_{judge_slug}_checkpoint.jsonl"
    results = run_anchor_pairs(llm, args.repeats, checkpoint_path)
    report = render_report(results, args.judge, model_name, args.repeats)

    out_path = DOCS_DIR / f"eval_pairwise_anchor_{judge_slug}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    raw_path = DOCS_DIR / f"eval_pairwise_anchor_{judge_slug}_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(
            [{"id": r["pair"]["id"], "final": r["final"]} for r in results],
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(report)
    print(f"저장 완료: {out_path} (원자료: {raw_path})")


if __name__ == "__main__":
    main()
