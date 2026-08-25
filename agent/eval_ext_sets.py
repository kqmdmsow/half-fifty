"""확장 세트(임대차 ext + 금융 finance) 1회 측정 — 도메인 전이 실험 포함.

`eval_real_labels.py`(공식 Test 40 전용)와 분리된 스크립트로,
검수 통과분 확장 세트 2개를 현재 파이프라인(analysis._analyze_clause)으로
1회 측정한다. 집계 규칙은 eval_real_labels.py와 동일:
양성 = 예측 risk_level ∈ {주의, 위험}, 정답 양성 = gold_risk_level == 위험.

- data/real_clause_labels_ext.csv     : 임대차 확장 34건 (동일 도메인 일반화)
- data/real_clause_labels_finance.csv : 금융 33행 (도메인 전이 — 임대차로 튜닝된
  프롬프트를 수정 없이 적용, risk_type 불일치는 관찰 항목. #89에서 유형 편중
  해소 위해 확충 중)

결과는 docs/eval_ext_sets_transfer.md에 저장 (기존 문서 덮어쓰지 않음).

사용법: cd agent && python eval_ext_sets.py
"""

import csv
from pathlib import Path

from src.eval_repeat import RepeatRunner, SystemicFailureDetected
from src.nodes.analysis import _analyze_clause

# EVAL_WORKER=solar — 크레딧 소진 시 무료 워커로 대체 실행 (평가 전용 주입).
# 주의: 개별 조항의 폴백은 집계에서 제외하고 건수만 보고한다. 여러 조항이
# 연속으로 통째 폴백하면 SystemicFailureDetected로 중단된다 (#161).
import os
if os.getenv("EVAL_WORKER") == "solar":
    from langchain_openai import ChatOpenAI

    import src.nodes.analysis as _an

    _an.get_worker_llm = lambda: ChatOpenAI(
        model=os.getenv("MODEL_WORKER_SOLAR", "solar-pro3"), temperature=0,
        base_url="https://api.upstage.ai/v1",
        api_key=os.getenv("UPSTAGE_API_KEY"), max_retries=0)


DATA = Path(__file__).parent.parent / "data"

# 위치 인자는 기존 호출 방식과의 호환을 위해 유지한다:
#   python eval_ext_sets.py [출력파일명.md] [split목록]
import argparse
import json
import sys

_ap = argparse.ArgumentParser(description="확장 세트 측정 (ext + finance)")
_ap.add_argument("out_name", nargs="?", default="eval_ext_sets_transfer.md",
                 help="출력 마크다운 파일명")
_ap.add_argument("splits", nargs="?", default=None,
                 help="split 필터(쉼표 구분). 기본 test — 튜닝 중 회귀 확인은 'train,val'")
_ap.add_argument("--repeats", type=int, default=1, metavar="N",
                 help="조항별 반복 실행 횟수. 보고용 수치는 3 이상 권장 (#161)")
_ap.add_argument("--out", default=None, metavar="results.json",
                 help="회차별 원자료 JSON 저장 경로 (#161)")
_args = _ap.parse_args()

OUT_PATH = Path(__file__).parent.parent / "docs" / _args.out_name
_repeats = _args.repeats

SETS = [
    ("임대차 확장 (ext, 34건)", DATA / "real_clause_labels_ext.csv"),
    ("금융 전이 (finance, 33행)", DATA / "real_clause_labels_finance.csv"),
]

# split 필터. 기본 "test"(공식 집계) — 프롬프트 튜닝 중 회귀 확인은
# "train,val"로 실행해 test 오염을 피한다.
_splits = set(_args.splits.split(",")) if _args.splits else {"test"}

# note 필드에 이 마커가 있으면 측정은 하되(감사 추적용) 집계(TP/FP/FN/TN)에서는
# 뺀다 — 텍스트 자체가 원 조항이 아니라 재구성/부분인용이라 라벨 근거가 텍스트
# 안에 없는 행 (#56, fss_사례집1권 2010_ELS조건조정·2009_주식매수연기). 삭제가
# 아니라 보류: 원문을 확보하면 마커를 떼고 다시 집계에 넣는다.
_LABEL_HOLD_MARKER = "[라벨 품질 보류"


def run_set(name, path, runner):
    # 공식 집계는 held-out(test)만 — train/val 행은 프롬프트 튜닝용이라 제외
    # (오염 방지: 튜닝에 쓴 사례를 성능 수치에 섞지 않는다)
    all_rows = list(csv.DictReader(open(path, encoding="utf-8")))
    rows = [r for r in all_rows if r["split"] in _splits]
    if len(all_rows) != len(rows):
        print(f"({name}: train/val {len(all_rows) - len(rows)}행은 집계 제외)")
    results = []
    held = 0
    for r in rows:
        outcome = runner.run(
            lambda text=r["clause_text"]: _analyze_clause("clause_001", text),
            label=r["case_id"],
        )
        if outcome.fully_fallback:
            # 전 회차 폴백 — 정답과 대조할 수 없어 분모에서도 뺀다
            print(f"[!] {r['case_id']}: 전체 폴백 {outcome.fallback_count}/{runner.repeats}"
                  f" — 집계 제외")
            continue
        pred = outcome.prediction
        gold_pos = r["gold_risk_level"] == "위험"
        pred_pos = pred["risk_level"] in ("주의", "위험")
        ok = gold_pos == pred_pos
        mark = "O" if ok else "X"
        spread = "" if runner.repeats == 1 else f" ({'/'.join(p['risk_level'] for p in outcome.runs)})"
        flag = " [과반없음]" if outcome.tie else ""
        fb = f" [폴백 {outcome.fallback_count}/{runner.repeats}]" if outcome.fallback_count else ""
        hold = _LABEL_HOLD_MARKER in r["note"]
        if hold:
            held += 1
            print(f"[{mark}] {r['case_id']}: gold={r['gold_risk_level']}/{r['gold_risk_type']}"
                  f" -> pred={pred['risk_level']}/{pred['risk_type']}{spread}{flag}{fb}"
                  f" [라벨 품질 보류 — 집계 제외]")
            continue
        results.append({"row": r, "pred": pred, "ok": ok, "runs": outcome.runs,
                        "tie": outcome.tie, "fallback_count": outcome.fallback_count})
        print(f"[{mark}] {r['case_id']}: gold={r['gold_risk_level']}/{r['gold_risk_type']}"
              f" -> pred={pred['risk_level']}/{pred['risk_type']}{spread}{flag}{fb}")
    if held:
        print(f"({name}: 라벨 품질 보류 {held}건은 집계 제외 — 측정 결과는 위에 기록)")
    tp = sum(1 for x in results if x["row"]["gold_risk_level"] == "위험" and x["pred"]["risk_level"] in ("주의", "위험"))
    fn = sum(1 for x in results if x["row"]["gold_risk_level"] == "위험" and x["pred"]["risk_level"] == "안전")
    fp = sum(1 for x in results if x["row"]["gold_risk_level"] == "안전" and x["pred"]["risk_level"] in ("주의", "위험"))
    tn = sum(1 for x in results if x["row"]["gold_risk_level"] == "안전" and x["pred"]["risk_level"] == "안전")
    return results, (tp, fp, fn, tn)


def fmt(v):
    return f"{v:.2f}" if v == v and v is not None else "-"


def main():
    runner = RepeatRunner(repeats=_repeats)
    if _repeats == 1:
        print("주의: --repeats 1은 단발 측정이다. temperature=0에서도 판정이 회차마다 "
              "뒤집히므로 보고용 수치는 --repeats 3 이상으로 낼 것 (#161).")
    lines = [
        "# 확장 세트 측정 — 임대차 일반화 + 금융 도메인 전이",
        "",
        f"> 측정 조건: {runner.summary()}",
        "",
        "검수 통과분 확장 세트를 현재 파이프라인(worker `claude-haiku-4-5`, "
        "analysis.txt 튜닝 상태 그대로)으로 측정. 공식 Test 40 수치"
        "(docs/eval_real_labels_claude_pr18.md, P0.79/R0.83/Acc0.78)와 별도 세트이므로 "
        "직접 합산 금지. 금융 세트는 임대차로 튜닝된 프롬프트를 수정 없이 적용한 "
        "**도메인 전이 실험** — risk_type 불일치는 실패가 아니라 관찰 항목.",
        "",
    ]
    per_set = {}
    for name, path in SETS:
        results, (tp, fp, fn, tn) = run_set(name, path, runner)
        per_set[name] = results
        n = len(results)
        prec = tp / (tp + fp) if tp + fp else None
        rec = tp / (tp + fn) if tp + fn else None
        acc = (tp + tn) / n
        lines += [
            f"## {name}",
            "",
            "| TP | FP | FN | TN | Precision | Recall | Accuracy |",
            "|---|---|---|---|---|---|---|",
            f"| {tp} | {fp} | {fn} | {tn} | {fmt(prec) if prec is not None else '-'} | "
            f"{fmt(rec) if rec is not None else '-'} | {fmt(acc)} |",
            "",
            "### 건별 결과",
            "",
            "| case_id | 정답(level/type) | 예측(level/type) | 일치 |",
            "|---|---|---|---|",
        ]
        for x in results:
            r, p = x["row"], x["pred"]
            lines.append(
                f"| {r['case_id']} | {r['gold_risk_level']}/{r['gold_risk_type']} | "
                f"{p['risk_level']}/{p['risk_type']} | {'O' if x['ok'] else 'X'} |"
            )
        lines.append("")
    # 폴백·tie 집계는 전 세트를 돌고 나야 확정되므로 머리말을 마지막에 갱신한다
    for i, line in enumerate(lines):
        if line.startswith("> 측정 조건: "):
            lines[i] = f"> 측정 조건: {runner.summary()}"
            break
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"저장 완료: {OUT_PATH}")
    print(f"측정 조건: {runner.summary()}")

    if _args.out:
        raw = {
            "repeats": _repeats,
            "condition": runner.summary(),
            "sets": {
                name: [
                    {
                        "case_id": x["row"]["case_id"],
                        "split": x["row"]["split"],
                        "gold_risk_level": x["row"]["gold_risk_level"],
                        "gold_risk_type": x["row"]["gold_risk_type"],
                        "runs": [{"risk_level": p["risk_level"], "risk_type": p["risk_type"]}
                                 for p in x["runs"]],
                        "final_risk_level": x["pred"]["risk_level"],
                        "final_risk_type": x["pred"]["risk_type"],
                        "tie": x["tie"],
                        "fallback_count": x["fallback_count"],
                    }
                    for x in rs
                ]
                for name, rs in per_set.items()
            },
            "fully_fallback": runner.fully_fallback_labels,
        }
        out_path = Path(_args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"원자료 저장: {out_path}")


if __name__ == "__main__":
    try:
        main()
    except SystemicFailureDetected as exc:
        sys.exit(f"\n중단: {exc}")
