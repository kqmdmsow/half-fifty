"""확장 세트(임대차 ext + 금융 finance) 1회 측정 — 도메인 전이 실험 포함.

`eval_real_labels.py`(공식 Test 40 전용)와 분리된 스크립트로,
검수 통과분 확장 세트 2개를 현재 파이프라인(analysis._analyze_clause)으로
1회 측정한다. 집계 규칙은 eval_real_labels.py와 동일:
양성 = 예측 risk_level ∈ {주의, 위험}, 정답 양성 = gold_risk_level == 위험.

- data/real_clause_labels_ext.csv     : 임대차 확장 14건 (동일 도메인 일반화)
- data/real_clause_labels_finance.csv : 금융 8행 (도메인 전이 — 임대차로 튜닝된
  프롬프트를 수정 없이 적용, risk_type 불일치는 관찰 항목)

결과는 docs/eval_ext_sets_transfer.md에 저장 (기존 문서 덮어쓰지 않음).

사용법: cd agent && python eval_ext_sets.py
"""

import csv
from pathlib import Path

from src.nodes.analysis import _analyze_clause

DATA = Path(__file__).parent.parent / "data"
OUT_PATH = Path(__file__).parent.parent / "docs" / "eval_ext_sets_transfer.md"

SETS = [
    ("임대차 확장 (ext, 14건)", DATA / "real_clause_labels_ext.csv"),
    ("금융 전이 (finance, 8행)", DATA / "real_clause_labels_finance.csv"),
]


def run_set(name, path):
    # 공식 집계는 held-out(test)만 — train/val 행은 프롬프트 튜닝용이라 제외
    # (오염 방지: 튜닝에 쓴 사례를 성능 수치에 섞지 않는다)
    all_rows = list(csv.DictReader(open(path, encoding="utf-8")))
    rows = [r for r in all_rows if r["split"] == "test"]
    if len(all_rows) != len(rows):
        print(f"({name}: train/val {len(all_rows) - len(rows)}행은 집계 제외)")
    results = []
    for r in rows:
        pred = _analyze_clause("clause_001", r["clause_text"])
        gold_pos = r["gold_risk_level"] == "위험"
        pred_pos = pred["risk_level"] in ("주의", "위험")
        ok = gold_pos == pred_pos
        results.append({"row": r, "pred": pred, "ok": ok})
        mark = "O" if ok else "X"
        print(f"[{mark}] {r['case_id']}: gold={r['gold_risk_level']}/{r['gold_risk_type']}"
              f" -> pred={pred['risk_level']}/{pred['risk_type']}")
    tp = sum(1 for x in results if x["row"]["gold_risk_level"] == "위험" and x["pred"]["risk_level"] in ("주의", "위험"))
    fn = sum(1 for x in results if x["row"]["gold_risk_level"] == "위험" and x["pred"]["risk_level"] == "안전")
    fp = sum(1 for x in results if x["row"]["gold_risk_level"] == "안전" and x["pred"]["risk_level"] in ("주의", "위험"))
    tn = sum(1 for x in results if x["row"]["gold_risk_level"] == "안전" and x["pred"]["risk_level"] == "안전")
    return results, (tp, fp, fn, tn)


def fmt(v):
    return f"{v:.2f}" if v == v and v is not None else "-"


def main():
    lines = [
        "# 확장 세트 1회 측정 — 임대차 일반화 + 금융 도메인 전이 (2026-08-06)",
        "",
        "검수 통과분 확장 세트를 현재 파이프라인(worker `claude-haiku-4-5`, "
        "analysis.txt 튜닝 상태 그대로)으로 **각 1회** 측정. 공식 Test 40 수치"
        "(docs/eval_real_labels_claude_pr18.md, P0.79/R0.83/Acc0.78)와 별도 세트이므로 "
        "직접 합산 금지. 금융 세트는 임대차로 튜닝된 프롬프트를 수정 없이 적용한 "
        "**도메인 전이 실험** — risk_type 불일치는 실패가 아니라 관찰 항목.",
        "",
    ]
    for name, path in SETS:
        results, (tp, fp, fn, tn) = run_set(name, path)
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
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
