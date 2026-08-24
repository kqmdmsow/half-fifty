"""정상 계약서(기관 제정 표준 양식) 문서 단위 오탐(FP) 측정.

data/normal_contracts/manifest.csv의 문서를 실사용 흐름 그대로
(파서 분할 → 조항 분석) 통과시켜, "위험을 심지 않은 표준 양식에서
위험/주의가 몇 건 뜨는가"를 잰다. 골든셋 조항 단위 안전 라벨
(eval_real_labels.py의 FP 셀)과 달리 문서 단위·파서 포함이 차이점.

집계 규칙은 기존 평가와 동일: 양성 = 예측 risk_level ∈ {주의, 위험}.
표준 양식 전제상 전 조항 기대값이 안전이므로 양성 = FP. 단 '주의'는
표준 양식의 실제 의무 조항(원상회복·연체 해지 등)에 대한 보수적 안내일
수 있어 위험/주의를 분리 집계하고, 양성 조항 전건의 근거를 리포트에
남겨 사람이 재검수한다.

사용법: cd agent && python eval_normal_fp.py [출력파일명.md]
결과: docs/eval_normal_fp.md (기본)
"""

import csv
import sys
from pathlib import Path

from src.eval_repeat import RepeatRunner, SystemicFailureDetected
from src.nodes.analysis import _analyze_clause
from src.nodes.parser import split_clauses_with_warnings

# EVAL_WORKER=solar — 크레딧 소진 시 무료 워커 대체 (eval_ext_sets.py와 동일)
import os
if os.getenv("EVAL_WORKER") == "solar":
    from langchain_openai import ChatOpenAI

    import src.nodes.analysis as _an

    _an.get_worker_llm = lambda: ChatOpenAI(
        model=os.getenv("MODEL_WORKER_SOLAR", "solar-pro3"), temperature=0,
        base_url="https://api.upstage.ai/v1",
        api_key=os.getenv("UPSTAGE_API_KEY"), max_retries=0)

BASE = Path(__file__).parent.parent / "data" / "normal_contracts"

import argparse
import json

_ap = argparse.ArgumentParser(description="정상 계약서 문서 단위 오탐 측정")
_ap.add_argument("out_name", nargs="?", default="eval_normal_fp.md",
                 help="출력 마크다운 파일명")
_ap.add_argument("--repeats", type=int, default=1, metavar="N",
                 help="조항별 반복 실행 횟수. 보고용 수치는 3 이상 권장 (#161)")
_ap.add_argument("--out", default=None, metavar="results.json",
                 help="조항별 원자료 JSON 저장 경로 (#161)")
_ap.add_argument("--split", default=None, metavar="val|test",
                 help="manifest의 split 컬럼으로 문서를 거른다. 튜닝(#156)에는 val, "
                      "최종 수치에는 test — 섞으면 튜닝한 문서로 보고하게 된다")
_args = _ap.parse_args()

OUT_PATH = Path(__file__).parent.parent / "docs" / _args.out_name


def run_doc(row, runner):
    """문서 하나를 조항 단위로 측정. 순차 실행 — 병렬(5-way)에서는 부하성
    실패가 재현됐고(폴백이 risk_level=주의라 FP를 부풀림), 순차에서는 전 조항
    성공을 확인했다. 벤치마크는 속도보다 수치 정확성이 우선.

    기존의 '실패 시 최대 2라운드 재시도'는 RepeatRunner가 대체한다 — 회차별
    결과에서 폴백을 빼고 남은 것으로 다수결하므로, repeats를 올리면 일시 실패
    회수와 판정 안정화가 함께 된다.
    """
    text = (BASE / row["file"]).read_text(encoding="utf-8")
    clauses, warns = split_clauses_with_warnings(text)
    outcomes = [
        runner.run(lambda c=c: _analyze_clause(c["clause_id"], c["text"]),
                   label=f"{row['doc_id']}/{c['clause_id']}")
        for c in clauses
    ]
    preds = [o.prediction for o in outcomes]
    flagged = [(c, o.prediction) for c, o in zip(clauses, outcomes)
               if not o.fully_fallback and o.prediction["risk_level"] in ("주의", "위험")]
    failed = [(c, o) for c, o in zip(clauses, outcomes) if o.fully_fallback]
    return clauses, preds, flagged, failed, warns, outcomes


def main():
    rows = list(csv.DictReader(open(BASE / "manifest.csv", encoding="utf-8")))
    if _args.split:
        before = len(rows)
        rows = [r for r in rows if r.get("split") == _args.split]
        print(f"split={_args.split} 필터: {before}문서 → {len(rows)}문서")
        if not rows:
            sys.exit(f"split={_args.split}에 해당하는 문서가 없다 — manifest.csv 확인")
    runner = RepeatRunner(repeats=_args.repeats)
    if _args.repeats == 1:
        print("주의: --repeats 1은 단발 측정이다. 보고용 수치는 --repeats 3 이상 (#161).")
    lines = ["# 정상 계약서(표준 양식) 문서 단위 오탐 측정", "",
             "실행: `python eval_normal_fp.py` — 워커 "
             f"`{os.getenv('MODEL_WORKER', '(기본)')}`, 코퍼스는 "
             "data/normal_contracts/README.md 참조.", "",
             "'실패 폴백'은 인용 검증(citation_check) 등으로 재시도가 소진돼",
             "보수적 '주의'로 노출된 조항 — 모델의 위험 판정과 성격이 달라",
             "분리 집계한다 (사용자 화면에는 둘 다 '주의'로 보임).", "",
             "| 문서 | 조항 | 안전 | 주의(판정) | 위험(판정) | 실패 폴백 | 화면 FP율 |",
             "|---|---|---|---|---|---|---|"]
    detail = ["", "## 양성(주의/위험) 판정 전건 — 사람 재검수용", ""]
    total = dict(n=0, caution=0, danger=0, failed=0)
    raw_docs = {}
    for row in rows:
        clauses, preds, flagged, failed, warns, outcomes = run_doc(row, runner)
        raw_docs[row["doc_id"]] = [
            {
                "clause_id": c["clause_id"],
                "runs": [{"risk_level": q["risk_level"], "risk_type": q["risk_type"]}
                         for q in o.runs],
                "final_risk_level": None if o.fully_fallback else o.prediction["risk_level"],
                "final_risk_type": None if o.fully_fallback else o.prediction["risk_type"],
                "tie": o.tie,
                "fallback_count": o.fallback_count,
                "fully_fallback": o.fully_fallback,
            }
            for c, o in zip(clauses, outcomes)
        ]
        caution = sum(1 for _, p in flagged if p["risk_level"] == "주의")
        danger = sum(1 for _, p in flagged if p["risk_level"] == "위험")
        total["n"] += len(clauses)
        total["caution"] += caution
        total["danger"] += danger
        total["failed"] += len(failed)
        rate = (caution + danger + len(failed)) / len(clauses) * 100
        print(f"[{row['doc_id']}] {len(clauses)}조항 → 주의 {caution}, 위험 {danger}, "
              f"실패폴백 {len(failed)} (화면 FP {rate:.0f}%)")
        lines.append(f"| {row['doc_id']} ({row['title']}) | {len(clauses)} | "
                     f"{len(clauses) - caution - danger - len(failed)} | {caution} | "
                     f"{danger} | {len(failed)} | {rate:.0f}% |")
        for c, p in flagged:
            detail.append(f"### {row['doc_id']} / {c['clause_id']} — **{p['risk_level']} / {p['risk_type']}**")
            detail.append(f"- 조항: {c['text'][:160]}")
            detail.append(f"- 근거: {p['risk_evidence'][:300]}")
            detail.append("")
        for c, _o in failed:
            detail.append(f"### {row['doc_id']} / {c['clause_id']} — **전체 폴백** (집계 제외)")
            detail.append(f"- 조항: {c['text'][:160]}")
            detail.append("")
    screen = total["caution"] + total["danger"] + total["failed"]
    rate = screen / total["n"] * 100
    lines.append(f"| **합계** | {total['n']} | {total['n'] - screen} | "
                 f"{total['caution']} | {total['danger']} | {total['failed']} | {rate:.0f}% |")
    lines.insert(1, f"\n> 측정 조건: {runner.summary()}"
                    + (f" / split={_args.split}" if _args.split else ""))
    OUT_PATH.write_text("\n".join(lines + detail), encoding="utf-8")
    if _args.out:
        out_path = Path(_args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(
            {"repeats": _args.repeats, "condition": runner.summary(),
             "split": _args.split, "docs": raw_docs},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"원자료 저장: {out_path}")
    print(f"\n합계: {total['n']}조항 — 판정 주의 {total['caution']} + 위험 {total['danger']}"
          f" + 실패폴백 {total['failed']} = 화면 FP율 {rate:.1f}%")
    print(f"저장: {OUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except SystemicFailureDetected as exc:
        sys.exit(f"\n중단: {exc}")
