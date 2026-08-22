"""정부/법원 판정 기반 실물 조항 정답지(data/real_clause_labels.csv) 평가 스크립트.

왜 별도 스크립트인가: `eval.py`는 `data/`의 완전한 계약서 5건을 Parser로 조항
분리한 뒤 파이프라인 전체(Parser->Analysis->Persona->Judge)를 돌린다. 그런데
`real_clause_labels.csv`는 hldcc.or.kr 조정사례·LBox Open 판례·AI Hub 서식에서
"이미 조항 하나 단위로 추출된" 44개 골든 라벨이지, 원본 그대로의 완전한 계약서
문서가 아니다(각 사례는 판결문·조정문 전체에서 실제 인용된 조항 한 줄만 뽑아온
것). 그래서 Parser를 거칠 필요가 없고, 오히려 Analysis Agent의 핵심 로직
(`src.nodes.analysis._analyze_clause`)을 조항 단위로 직접 호출하는 게 데이터
형태에 맞는 평가 방식이다 — Persona/Judge는 조항 판정 자체와 무관하므로 생략한다.

data/labels.md 기반 5건(자작 위험 삽입)과 이 44건(정부·법원이 실제로 무효/유효
판정한 조항)은 신뢰도 등급이 다르다 — 이쪽이 훨씬 강한 정답지다.

사용법:
    cd agent
    source .venv/bin/activate
    python eval_real_labels.py
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

from src.nodes.analysis import _FALLBACK_EVIDENCE, _analyze_clause

# EVAL_WORKER=solar — 크레딧 소진 시 무료 워커로 대체 실행 (평가 전용 주입).
# 주의: _analyze_clause 폴백이 오류를 은폐하므로, 실행 후 출력에서
# "분석 실패" 라인이 0건임을 반드시 확인할 것.
import os
if os.getenv("EVAL_WORKER") == "solar":
    from langchain_openai import ChatOpenAI

    import src.nodes.analysis as _an

    _an.get_worker_llm = lambda: ChatOpenAI(
        model=os.getenv("MODEL_WORKER_SOLAR", "solar-pro3"), temperature=0,
        base_url="https://api.upstage.ai/v1",
        api_key=os.getenv("UPSTAGE_API_KEY"), max_retries=0)


LABELS_PATH = Path(__file__).parent.parent / "data" / "real_clause_labels.csv"

# 기본 출력은 베이스라인 문서 — 덮어쓰기 사고 방지를 위해 인자로 출력 파일명을 받는다.
# 위치 인자는 기존 호출 방식과의 호환을 위해 유지한다:
#   python eval_real_labels.py [출력파일명.md] [split목록]
import argparse
import json
import sys

_ap = argparse.ArgumentParser(description="공식 조항 정답지 평가 (real_clause_labels.csv)")
_ap.add_argument("out_name", nargs="?", default="eval_real_labels_claude.md",
                 help="출력 마크다운 파일명 (재실행 시 새 이름을 줄 것)")
_ap.add_argument("splits", nargs="?", default=None,
                 help="실행할 split 목록(쉼표 구분). 오염 방지 — 튜닝 중에는 'train,val'만")
_ap.add_argument("--repeats", type=int, default=1, metavar="N",
                 help="조항별 반복 실행 횟수. 보고용 수치는 3 이상 권장 (#161) — "
                      "temperature=0에서도 판정이 회차마다 뒤집히기 때문 "
                      "(docs/reproducibility.md: 24조항 중 1건). 기본 1")
_ap.add_argument("--out", default=None, metavar="results.json",
                 help="회차별 원자료 JSON 저장 경로. 수치가 움직였을 때 "
                      "재실행 없이 원인을 되짚으려면 반드시 남길 것 (#161)")
_args = _ap.parse_args()

OUT_PATH = Path(__file__).parent.parent / "docs" / _args.out_name
_splits = set(_args.splits.split(",")) if _args.splits else None


def _load_labels() -> list:
    with open(LABELS_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if _splits:
        rows = [r for r in rows if r["split"] in _splits]
    return rows


class FallbackDetected(RuntimeError):
    """폴백 응답을 감지했을 때 즉시 중단시키는 예외.

    `_analyze_clause`는 실패를 '주의/해당 없음'으로 흡수한다. 2026-08-07 AI Hub
    실행에서 크레딧이 소진된 뒤 이 폴백이 정상 결과처럼 기록돼 strong 82%라는
    오염 수치가 나왔고, 2026-08-22 재측정에서도 같은 원인으로 중단됐다
    (docs/eval_aihub580_full_run.md). 평가 하네스에서 폴백은 데이터가 아니라
    사고이므로, 한 건이라도 나오면 부분 결과를 남기고 멈춘다.
    """


def _assert_not_fallback(clause_id: str, prediction: dict) -> None:
    if prediction.get("risk_evidence") == _FALLBACK_EVIDENCE:
        raise FallbackDetected(
            f"{clause_id}에서 폴백 응답 감지 — API 오류(크레딧 소진·인증·레이트리밋)일 "
            f"가능성이 높다. 원인을 확인한 뒤 재실행할 것. 폴백을 정상 결과로 집계하면 "
            f"수치가 조용히 오염된다."
        )


def _majority(levels: list) -> tuple:
    """회차별 risk_level 다수결. 반환: (확정 level, 과반 없음 여부)."""
    counts = Counter(levels)
    top, n = counts.most_common(1)[0]
    return top, n * 2 <= len(levels)


def run_eval(repeats: int = 1) -> list:
    rows = _load_labels()
    results = []
    for i, row in enumerate(rows):
        clause_id = f"real_{i:03d}_{row['case_id']}"
        runs = []
        for attempt in range(repeats):
            prediction = _analyze_clause(clause_id, row["clause_text"])
            _assert_not_fallback(clause_id, prediction)
            runs.append(prediction)

        # 다수결은 risk_level 기준. 확정 level을 낸 회차의 예측을 대표로 삼아야
        # risk_type·근거가 확정 level과 어긋나지 않는다.
        level, tie = _majority([p["risk_level"] for p in runs])
        prediction = next(p for p in runs if p["risk_level"] == level)

        results.append({"row": row, "prediction": prediction, "runs": runs, "tie": tie})
        gold = row["gold_risk_level"]
        match = "O" if (level != "안전") == (gold != "안전") else "X"
        flag = " [과반없음]" if tie else ""
        spread = "" if repeats == 1 else f" ({'/'.join(p['risk_level'] for p in runs)})"
        print(f"[{match}] {row['case_id']}: gold={gold}/{row['gold_risk_type']} -> "
              f"pred={level}/{prediction['risk_type']}{spread}{flag}")
    return results


def _confusion(results: list) -> dict:
    tp = fp = fn = tn = 0
    for r in results:
        gold_risk = r["row"]["gold_risk_level"] != "안전"
        pred_risk = r["prediction"]["risk_level"] != "안전"
        if gold_risk and pred_risk:
            tp += 1
        elif gold_risk and not pred_risk:
            fn += 1
        elif not gold_risk and pred_risk:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    accuracy = (tp + tn) / len(results) if results else None
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "accuracy": accuracy}


def _confusion_row(label: str, c: dict) -> str:
    if c["precision"] is None:
        return f"| {label} | {c['tp']} | {c['fp']} | {c['fn']} | {c['tn']} | - | - | - |"
    return (
        f"| {label} | {c['tp']} | {c['fp']} | {c['fn']} | {c['tn']} | "
        f"{c['precision']:.2f} | {c['recall']:.2f} | {c['accuracy']:.2f} |"
    )


def render_report(results: list) -> str:
    # docs/clause_level_dataset_and_split.md 3.2절 배정: 광고대행/신발도매/즉시연금2017-17=train,
    # 바로연금보험(즉시연금)2018-8=val, 나머지(hldcc/LBox/AI Hub)=test(신규 확보, 한 번도 안 본 데이터).
    test_results = [r for r in results if r["row"]["split"] == "test"]
    train_results = [r for r in results if r["row"]["split"] == "train"]
    val_results = [r for r in results if r["row"]["split"] == "val"]
    # label_grade: A=정부/법원 판정(hldcc/lbox), C=AI Hub 자체판단. Test 내에서만 분리.
    test_a_results = [r for r in test_results if r["row"].get("label_grade") == "A"]

    risk_type_confusion = defaultdict(Counter)  # gold_risk_type -> Counter(pred_risk_type), test만
    mismatches = []

    for r in results:
        gold_level = r["row"]["gold_risk_level"]
        gold_type = r["row"]["gold_risk_type"]
        pred_level = r["prediction"]["risk_level"]
        pred_type = r["prediction"]["risk_type"]
        # 방어 처리: risk_type이 TypedDict라 런타임 검증이 없어, LLM이 간혹 문자열
        # 대신 리스트를 반환한다(예: 다중 위험유형). 집계용으로만 문자열화한다.
        if not isinstance(pred_type, str):
            pred_type = ", ".join(pred_type) if isinstance(pred_type, (list, tuple)) else str(pred_type)
        gold_risk = gold_level != "안전"
        pred_risk = pred_level != "안전"

        if r["row"]["split"] == "test" and gold_risk:
            risk_type_confusion[gold_type][pred_type] += 1

        if gold_risk != pred_risk or (gold_risk and gold_type != pred_type):
            mismatches.append((r, gold_level, gold_type, pred_level, pred_type))

    test_c = _confusion(test_results)
    test_a_c = _confusion(test_a_results)

    lines = [
        "# 실물 조항 정답지(real_clause_labels.csv) 평가 결과",
        "",
        f"`data/real_clause_labels.csv`(정부/법원 판정 기반 {len(results)}건 — hldcc·LBox·"
        "AI Hub 자연발생 템플릿)에 대해 `analysis._analyze_clause()`를 직접 호출한 결과. "
        "Parser/Persona/Judge 없이 Analysis 로직만 단독 평가.",
        "",
        "**중요**: 이 중 4건(광고대행/신발도매/즉시연금2017-17/바로연금보험2018-8, "
        "`data/real_labels.md` 출처)은 `docs/clause_level_dataset_and_split.md`에서 이미 "
        "Train/Val로 지정된, 프롬프트 튜닝 이력이 있는 데이터다. 이 4건을 섞어서 낸 수치는 "
        "공정한 held-out 평가가 아니므로, **아래 'Test 전용(40건)' 표만 공식 베이스라인으로 "
        "취급**한다. Train/Val 결과는 참고용으로만 병기.",
        "",
        "## Test 전용 (신규 확보 데이터 40건 — 공식 베이스라인)",
        "",
        "| 구분 | TP | FP | FN | TN | Precision | Recall | Accuracy |",
        "|---|---|---|---|---|---|---|---|",
        _confusion_row("test 전체 (40건)", test_c),
        _confusion_row("test A등급만 (27건, 정부·법원 판정)", test_a_c),
        "",
        "A등급은 hldcc·LBox(정부/법원 판정), C등급은 AI Hub(자체 판단) 출처다. "
        "\"정부 판정 기반이라 신뢰도 높다\"는 주장을 인용할 땐 A등급만 뗀 수치를 써야 한다.",
        "",
        "## 참고: Train/Val 서브셋 (튜닝 이력 있음, 공식 수치 아님)",
        "",
        "| 구분 | TP | FP | FN | TN | Precision | Recall | Accuracy |",
        "|---|---|---|---|---|---|---|---|",
        _confusion_row("train (3건)", _confusion(train_results)),
        _confusion_row("val (1건)", _confusion(val_results)),
        "",
        "## risk_type 혼동행렬 (Test 전용, 정답이 '위험'인 경우만, gold_type -> predicted_type 분포)",
        "",
        "| 정답 risk_type | 예측 분포 |",
        "|---|---|",
    ]
    for gold_type, counter in risk_type_confusion.items():
        dist = ", ".join(f"{k}:{v}" for k, v in counter.most_common())
        lines.append(f"| {gold_type} | {dist} |")

    lines += [
        "",
        f"## 불일치 사례 (전체 {len(mismatches)}건, split 포함)",
        "",
        "| 출처 | split | 정답(level/type) | 예측(level/type) | 조항 발췌 |",
        "|---|---|---|---|---|",
    ]
    for r, gl, gt, pl, pt in mismatches:
        excerpt = r["row"]["clause_text"][:40].replace("|", "/")
        lines.append(
            f"| {r['row']['case_id']} | {r['row']['split']} | {gl}/{gt} | {pl}/{pt} | {excerpt}... |"
        )

    if not mismatches:
        lines.append("| (없음) | | | | |")

    return "\n".join(lines) + "\n"


def _dump_raw(results: list, path: Path, repeats: int) -> None:
    """회차별 원자료 저장 — 수치가 움직였을 때 재실행 없이 대조하기 위한 것 (#161)."""
    payload = {
        "repeats": repeats,
        "n": len(results),
        "items": [
            {
                "case_id": r["row"]["case_id"],
                "split": r["row"]["split"],
                "label_grade": r["row"].get("label_grade"),
                "gold_risk_level": r["row"]["gold_risk_level"],
                "gold_risk_type": r["row"]["gold_risk_type"],
                "runs": [
                    {"risk_level": p["risk_level"], "risk_type": p["risk_type"],
                     "risk_evidence": p.get("risk_evidence")}
                    for p in r["runs"]
                ],
                "final_risk_level": r["prediction"]["risk_level"],
                "final_risk_type": r["prediction"]["risk_type"],
                "tie": r["tie"],
            }
            for r in results
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    repeats = _args.repeats
    if repeats < 1:
        sys.exit("--repeats는 1 이상이어야 한다")
    if repeats == 1:
        print("주의: --repeats 1은 단발 측정이다. temperature=0에서도 판정이 회차마다 "
              "뒤집히므로(±1~2건) 보고용 수치는 --repeats 3 이상으로 낼 것 (#161).")

    try:
        results = run_eval(repeats)
    except FallbackDetected as exc:
        sys.exit(f"\n중단: {exc}")

    if _args.out:
        raw_path = Path(_args.out)
        _dump_raw(results, raw_path, repeats)
        print(f"원자료 저장: {raw_path}")

    report = render_report(results)
    ties = sum(1 for r in results if r["tie"])
    header = (f"> 측정 조건: 조항별 {repeats}회 실행 후 risk_level 다수결"
              f"{f' / 과반 없음 {ties}건' if repeats > 1 else ' (단발 — 보고용 아님)'}\n\n")
    report = header + report
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
