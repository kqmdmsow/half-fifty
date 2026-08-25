"""종단 간 평가 — 파일 입력부터 Judge까지, 어느 단계 실패든 실패로 센다 (#174).

## 왜 필요한가

기존 평가는 전부 **조항 단위**다. `_analyze_clause`에 이미 잘 잘린 조항
텍스트를 넣고 판정만 본다. 그런데 실사용에서 사용자가 넣는 것은 조항이 아니라
**파일**이고, 판정 전에 실패할 수 있는 단계가 넷이나 더 있다:

    파일 → 추출(PDF/OCR) → 파서 → 도메인 → 분석 → 페르소나 → Judge

조항 단위 평가는 이 넷을 통째로 건너뛴다. 그래서 "정확도 67.5%"라고 말해도
사용자가 PDF를 올렸을 때 실제로 답을 받을 확률은 그보다 낮을 수 있다.
파서가 조항을 못 잘라도, 추출이 깨져도, 조항 단위 지표는 멀쩡하다.

**이 하네스는 시스템 실패를 전부 실패로 센다.** 추출 실패·파서 0조항·분석
폴백·Judge 재검토 필요를 각각 집계하고, "사용자가 쓸 만한 결과를 받았는가"를
최종 지표로 낸다.

## 무엇을 재는가

- **종단 간 성공률**: 파일을 넣어 판정까지 도달한 비율.
- **단계별 실패**: 어디서 깨지는지 분해. 개선 우선순위를 여기서 정한다.
- **종단 간 오탐**: 정답이 "전 조항 안전"인 표준 양식에서 위험·주의가 몇 건
  뜨는가. 파서 손실까지 포함한 실사용 오탐이다.

사용법: cd agent && python eval_end_to_end.py [출력.md]
  PERSONA=adult|senior|foreigner   기본 adult
"""

import os
import sys
import traceback
from pathlib import Path

from src.graph import run_pipeline
from src.ocr import OcrUnavailableError, document_parse_text
from src.pdf_extract import extract_with_hidden_report, hidden_text_notice

REPO = Path(__file__).parent.parent
OUT = REPO / "docs" / (sys.argv[1] if len(sys.argv) > 1 else "eval_end_to_end.md")
PERSONA = os.getenv("PERSONA", "adult")

# (표시명, 경로, 기대) — 기대가 "전 조항 안전"이면 양성 판정이 곧 오탐이다.
DOCS = [
    ("주택임대차표준계약서 (PDF)",
     "frontend/public/samples/sample_lease_standard.pdf", "전 조항 안전"),
    ("상가건물임대차표준계약서 (PDF)",
     "data/raw/normal_contract_sources/상가건물임대차표준계약서_2026게시.pdf", "전 조항 안전"),
    ("예금거래기본약관 (PDF)",
     "data/raw/pdf/[제10012호] 예금거래기본약관(2024.09.27. 개정).pdf", "전 조항 안전"),
    ("신탁 특약 계약서 사진 (OCR)",
     "frontend/public/samples/sample_lease_photo.jpg", "위험 포함"),
]


def _extract(path: Path) -> tuple[str, list[str]]:
    """실사용과 같은 경로로 텍스트를 뽑는다 (main.py의 분기와 동일)."""
    raw = path.read_bytes()
    if path.suffix.lower() == ".pdf":
        text, hidden = extract_with_hidden_report(raw)
        if text.strip():
            return text, ([hidden_text_notice(hidden)] if hidden else [])
        # 텍스트 레이어 없음 → OCR 폴백
    return document_parse_text(raw, path.name), []


def run_one(title: str, rel: str, expected: str) -> dict:
    row = {"title": title, "expected": expected, "stage": "-", "clauses": 0,
           "danger": 0, "caution": 0, "fallback": 0, "withheld": 0,
           "needs_review": False, "ok": False, "error": ""}
    path = REPO / rel
    if not path.exists():
        row["stage"] = "파일 없음"
        row["error"] = rel
        return row

    try:
        text, warns = _extract(path)
    except (OcrUnavailableError, ValueError) as exc:
        row["stage"] = "추출 실패"
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row

    try:
        state = run_pipeline(text, persona=PERSONA, extra_warnings=warns)
    except Exception as exc:  # 파이프라인 전체가 죽는 경우도 실패로 센다
        row["stage"] = "파이프라인 예외"
        row["error"] = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
        return row

    results = state["adapted_results"]
    row["clauses"] = len(state["clauses"])
    if not results:
        row["stage"] = "파서 0조항"
        return row

    row["danger"] = sum(r["risk_level"] == "위험" for r in results)
    row["caution"] = sum(r["risk_level"] == "주의" for r in results)
    row["fallback"] = sum(bool(r.get("analysis_failed")) for r in results)
    row["withheld"] = sum(bool(r.get("verdict_withheld")) for r in results)
    row["needs_review"] = bool(state.get("needs_review"))
    row["stage"] = "완주"
    # 사용자가 쓸 만한 결과를 받았는가 — 조항이 나왔고 전부 폴백이 아니면 성공.
    row["ok"] = row["fallback"] < len(results)
    return row


def main():
    print(f"종단 간 평가 — 문서 {len(DOCS)}건, 페르소나 {PERSONA}")
    rows = [run_one(*d) for d in DOCS]
    for r in rows:
        print(f"[{r['stage']:8s}] {r['title']} — 조항 {r['clauses']}, "
              f"위험 {r['danger']} 주의 {r['caution']} 폴백 {r['fallback']}"
              + (f"  ← {r['error']}" if r["error"] else ""))

    n = len(rows)
    ok = sum(r["ok"] for r in rows)
    safe_docs = [r for r in rows if r["expected"] == "전 조항 안전" and r["clauses"]]
    fp_clauses = sum(r["danger"] + r["caution"] + r["fallback"] for r in safe_docs)
    fp_total = sum(r["clauses"] for r in safe_docs)

    L = ["# 종단 간 평가 — 파일 입력부터 Judge까지", "",
         f"문서 {n}건, 페르소나 `{PERSONA}`, 워커 `{os.getenv('MODEL_WORKER', '(기본)')}`", "",
         "## 왜 이 수치가 따로 필요한가", "",
         "기존 평가는 전부 조항 단위다. 이미 잘 잘린 조항 텍스트를 넣고 판정만 본다. ",
         "그런데 사용자가 넣는 것은 파일이고, 판정 전에 실패할 수 있는 단계가 넷 더 있다 ",
         "(추출·파서·도메인·페르소나). 조항 단위 지표는 그 넷을 건너뛴다.", "",
         f"- **종단 간 성공률: {ok}/{n} = {ok / n * 100:.0f}%** "
         f"— 파일을 넣어 쓸 만한 판정까지 도달한 비율",
         (f"- **종단 간 오탐률: {fp_clauses}/{fp_total} = {fp_clauses / fp_total * 100:.1f}%** "
          f"— 정답이 '전 조항 안전'인 표준 양식 {len(safe_docs)}건 기준. "
          f"파서 손실과 분석 폴백까지 포함한 실사용 오탐"
          if fp_total else "- 종단 간 오탐률: 측정 대상 없음"), "",
         "| 문서 | 기대 | 도달 단계 | 조항 | 위험 | 주의 | 폴백 | 판정보류 | 재검토 |",
         "|---|---|---|---|---|---|---|---|---|"]
    L += [f"| {r['title']} | {r['expected']} | {r['stage']} | {r['clauses']} | "
          f"{r['danger']} | {r['caution']} | {r['fallback']} | {r['withheld']} | "
          f"{'예' if r['needs_review'] else '-'} |" for r in rows]

    errors = [r for r in rows if r["error"]]
    if errors:
        L += ["", "## 실패 상세", ""]
        L += [f"- **{r['title']}** ({r['stage']}): `{r['error']}`" for r in errors]

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"\n종단 간 성공률 {ok}/{n}"
          + (f" · 종단 간 오탐 {fp_clauses}/{fp_total}" if fp_total else "")
          + f"\n저장: {OUT}")


if __name__ == "__main__":
    main()
