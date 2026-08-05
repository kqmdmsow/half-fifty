"""Train/Val 서브셋 진단 스크립트 (docs/clause_level_dataset_and_split.md 3.2절).

`eval_real_labels.py`(Test 40건, 공식 베이스라인)와 달리, 이 스크립트는 **자유롭게
반복 실행해도 되는** Train/Val 데이터로 프롬프트 개선 작업 중 "지금 성능이 얼마나
되는지" 빠르게 확인하기 위한 것이다. 대상:

- Train: sample_lease_contract.txt / contract_02_finance_loan.txt /
  contract_04_gym_membership.txt (각 문서를 parser.split_clauses()로 다시 쪼갠 뒤
  clause_level_labels.csv의 라벨과 매칭) + real_clause_labels.csv의 train 3건(고립 조항)
- Val: contract_03_lease_normal.txt / contract_05_molit_standard.txt /
  normal_deposit_terms.txt + real_clause_labels.csv의 val 1건

Parser/Analysis만 쓰고 Persona/Judge는 생략 — risk_level/risk_type 판정 자체의
정확도만 본다(eval_real_labels.py와 동일한 관점).

사용법:
    cd agent
    source .venv/bin/activate
    python eval_train_val.py
"""

import csv
from collections import defaultdict
from pathlib import Path

from src.nodes.analysis import _analyze_clause
from src.nodes.parser import split_clauses

DATA_DIR = Path(__file__).parent.parent / "data"
CLAUSE_LABELS_PATH = DATA_DIR / "clause_level_labels.csv"
REAL_LABELS_PATH = DATA_DIR / "real_clause_labels.csv"

# 문서 파일이 data/ 바로 아래 있지 않은 경우의 예외 경로
DOC_PATH_OVERRIDES = {
    "normal_deposit_terms.txt": DATA_DIR / "contracts" / "normal_deposit_terms.txt",
}


def _doc_path(filename: str) -> Path:
    return DOC_PATH_OVERRIDES.get(filename, DATA_DIR / filename)


def _load_full_doc_items(target_split: str) -> list:
    """clause_level_labels.csv에서 target_split 문서들을 실제로 파싱해 (clause_id, text, gold_risk) 추출."""
    with open(CLAUSE_LABELS_PATH, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == target_split]

    by_doc = defaultdict(dict)
    for r in rows:
        by_doc[r["document"]][r["clause_id"]] = r["label"]

    items = []
    for document, labels in by_doc.items():
        text = _doc_path(document).read_text(encoding="utf-8")
        clauses = split_clauses(text)
        for c in clauses:
            gold = labels.get(c["clause_id"])
            if gold is None:
                continue  # 라벨 없는 조항(정의조항 등 source_note 미기재)은 제외
            items.append({"id": f"{document}:{c['clause_id']}", "text": c["text"], "gold": gold})
    return items


def _load_isolated_items(target_split: str) -> list:
    with open(REAL_LABELS_PATH, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == target_split]
    return [
        {"id": f"{r['source']}:{r['case_id']}", "text": r["clause_text"], "gold": r["gold_risk_level"]}
        for r in rows
    ]


def _confusion(items: list, predictions: dict) -> dict:
    tp = fp = fn = tn = 0
    for item in items:
        gold_risk = item["gold"] != "안전"
        pred_risk = predictions[item["id"]]["risk_level"] != "안전"
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
    accuracy = (tp + tn) / len(items) if items else None
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "accuracy": accuracy}


def run_split(name: str) -> None:
    items = _load_full_doc_items(name) + _load_isolated_items(name)
    predictions = {}
    for item in items:
        pred = _analyze_clause(item["id"], item["text"])
        predictions[item["id"]] = pred
        match = "O" if (pred["risk_level"] != "안전") == (item["gold"] != "안전") else "X"
        print(f"[{name}][{match}] {item['id']}: gold={item['gold']} -> pred={pred['risk_level']}/{pred['risk_type']}")

    c = _confusion(items, predictions)
    print(f"\n=== {name} (n={len(items)}) ===")
    print(f"TP={c['tp']} FP={c['fp']} FN={c['fn']} TN={c['tn']}")
    if c["precision"] is not None:
        print(f"Precision={c['precision']:.2f} Recall={c['recall']:.2f} Accuracy={c['accuracy']:.2f}")
    print()


def main() -> None:
    run_split("train")
    run_split("val")


if __name__ == "__main__":
    main()
