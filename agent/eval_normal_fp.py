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
OUT_PATH = Path(__file__).parent.parent / "docs" / (
    sys.argv[1] if len(sys.argv) > 1 else "eval_normal_fp.md")


def _is_failed(pred):
    return "분석 실패" in pred.get("risk_evidence", "")


def run_doc(row):
    text = (BASE / row["file"]).read_text(encoding="utf-8")
    clauses, warns = split_clauses_with_warnings(text)
    # 순차 실행 — 병렬(5-way)에서는 부하성 실패가 재현됐고(폴백이
    # risk_level=주의라 FP를 부풀림), 순차에서는 전 조항 성공을 확인했다.
    # 벤치마크는 속도보다 수치 정확성이 우선.
    preds = [_analyze_clause(c["clause_id"], c["text"]) for c in clauses]
    # 그래도 남는 일시 실패는 재시도로 회수 — 최대 2라운드.
    for _ in range(2):
        idx = [i for i, p in enumerate(preds) if _is_failed(p)]
        if not idx:
            break
        for i in idx:
            preds[i] = _analyze_clause(clauses[i]["clause_id"], clauses[i]["text"])
    flagged = [(c, p) for c, p in zip(clauses, preds)
               if p["risk_level"] in ("주의", "위험") and not _is_failed(p)]
    failed = [(c, p) for c, p in zip(clauses, preds) if _is_failed(p)]
    return clauses, preds, flagged, failed, warns


def main():
    rows = list(csv.DictReader(open(BASE / "manifest.csv", encoding="utf-8")))
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
    for row in rows:
        clauses, preds, flagged, failed, warns = run_doc(row)
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
        for c, p in failed:
            detail.append(f"### {row['doc_id']} / {c['clause_id']} — **실패 폴백** (재시도 소진)")
            detail.append(f"- 조항: {c['text'][:160]}")
            detail.append("")
    screen = total["caution"] + total["danger"] + total["failed"]
    rate = screen / total["n"] * 100
    lines.append(f"| **합계** | {total['n']} | {total['n'] - screen} | "
                 f"{total['caution']} | {total['danger']} | {total['failed']} | {rate:.0f}% |")
    OUT_PATH.write_text("\n".join(lines + detail), encoding="utf-8")
    print(f"\n합계: {total['n']}조항 — 판정 주의 {total['caution']} + 위험 {total['danger']}"
          f" + 실패폴백 {total['failed']} = 화면 FP율 {rate:.1f}%")
    print(f"저장: {OUT_PATH}")


if __name__ == "__main__":
    main()
