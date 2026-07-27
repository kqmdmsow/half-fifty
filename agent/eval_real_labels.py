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
OUT_PATH = Path(__file__).parent.parent / "docs" / "eval_real_labels.md"


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


def render_report(results: list) -> str:
    tp = fp = fn = tn = 0
    risk_type_confusion = defaultdict(Counter)  # gold_risk_type -> Counter(pred_risk_type)
    mismatches = []

    for r in results:
        gold_level = r["row"]["gold_risk_level"]
        gold_type = r["row"]["gold_risk_type"]
        pred_level = r["prediction"]["risk_level"]
        pred_type = r["prediction"]["risk_type"]

        gold_risk = gold_level != "안전"
        pred_risk = pred_level != "안전"

        if gold_risk and pred_risk:
            tp += 1
        elif gold_risk and not pred_risk:
            fn += 1
        elif not gold_risk and pred_risk:
            fp += 1
        else:
            tn += 1

        if gold_risk:
            risk_type_confusion[gold_type][pred_type] += 1

        if gold_risk != pred_risk or (gold_risk and gold_type != pred_type):
            mismatches.append((r, gold_level, gold_type, pred_level, pred_type))

    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    accuracy = (tp + tn) / len(results) if results else None

    lines = [
        "# 실물 조항 정답지(real_clause_labels.csv) 평가 결과",
        "",
        f"`data/real_clause_labels.csv`(정부/법원 판정 기반 {len(results)}건 — hldcc·LBox·"
        "AI Hub 자연발생 템플릿)에 대해 `analysis._analyze_clause()`를 직접 호출한 결과. "
        "Parser/Persona/Judge 없이 Analysis 로직만 단독 평가.",
        "",
        "## risk_level 이진 판정 (위험 vs 안전)",
        "",
        f"| TP | FP | FN | TN | Precision | Recall | Accuracy |",
        f"|---|---|---|---|---|---|---|",
        f"| {tp} | {fp} | {fn} | {tn} | "
        f"{precision:.2f} | {recall:.2f} | {accuracy:.2f} |"
        if precision is not None else "| - | - | - | - | - | - | - |",
        "",
        "## risk_type 혼동행렬 (정답이 '위험'인 경우만, gold_type -> predicted_type 분포)",
        "",
        "| 정답 risk_type | 예측 분포 |",
        "|---|---|",
    ]
    for gold_type, counter in risk_type_confusion.items():
        dist = ", ".join(f"{k}:{v}" for k, v in counter.most_common())
        lines.append(f"| {gold_type} | {dist} |")

    lines += [
        "",
        f"## 불일치 사례 ({len(mismatches)}건)",
        "",
        "| 출처 | 정답(level/type) | 예측(level/type) | 조항 발췌 |",
        "|---|---|---|---|",
    ]
    for r, gl, gt, pl, pt in mismatches:
        excerpt = r["row"]["clause_text"][:40].replace("|", "/")
        lines.append(f"| {r['row']['case_id']} | {gl}/{gt} | {pl}/{pt} | {excerpt}... |")

    if not mismatches:
        lines.append("| (없음) | | | |")

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
