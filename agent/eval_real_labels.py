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

from src.nodes.analysis import _analyze_clause

LABELS_PATH = Path(__file__).parent.parent / "data" / "real_clause_labels.csv"
# 기본 출력은 베이스라인 문서 — 덮어쓰기 사고 방지를 위해 인자로 출력 파일명을 받는다.
# 사용: python eval_real_labels.py [출력파일명.md]  (재실행 시 반드시 새 파일명 지정)
import sys
_out_name = sys.argv[1] if len(sys.argv) > 1 else "eval_real_labels_claude.md"
OUT_PATH = Path(__file__).parent.parent / "docs" / _out_name


def _load_labels() -> list:
    with open(LABELS_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_eval() -> list:
    rows = _load_labels()
    results = []
    for i, row in enumerate(rows):
        clause_id = f"real_{i:03d}_{row['case_id']}"
        prediction = _analyze_clause(clause_id, row["clause_text"])
        results.append({"row": row, "prediction": prediction})
        gold = row["gold_risk_level"]
        pred = prediction["risk_level"]
        match = "O" if (pred != "안전") == (gold != "안전") else "X"
        print(f"[{match}] {row['case_id']}: gold={gold}/{row['gold_risk_type']} -> "
              f"pred={pred}/{prediction['risk_type']}")
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


def main() -> None:
    results = run_eval()
    report = render_report(results)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
