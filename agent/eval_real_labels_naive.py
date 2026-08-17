"""나이브 베이스라인 평가 — "그냥 LLM에게 물어보면 몇 점인가".

목적: 공식 Test 40건(real_clause_labels.csv)에서, 도메인 지식이 담긴 프롬프트
(10유형 체계·표준 조항 예외·법 지식)와 검증 체계(Pydantic·인용 검사·재시도)
없이 같은 모델(MODEL_WORKER)에 같은 조항을 단순히 물어봤을 때의 성적을 잰다.

`src/prompts/baseline.txt`(착수보고서 <표 6> Baseline)와 다르다: 그쪽은 지식은
동일하게 주고 파이프라인 '구조' 차이만 격리하는 비교군이고, 이 스크립트는
지식+검증을 전부 뺀 '맨몸 호출'이다. 두 비교군의 용도를 혼동하지 말 것.

오염 주의: 이 실행은 우리 시스템을 튜닝하지 않는다 — 별개 비교군을 Test에
1회 측정하는 것이므로 held-out 원칙(개선 확정 시 1회)과 충돌하지 않는다.

사용법:
    cd agent
    .venv/bin/python eval_real_labels_naive.py eval_real_labels_naive_baseline.md test
"""

import csv
import json
import os
import sys
from pathlib import Path

from src.llm import get_worker_llm

_NAIVE_PROMPT = """다음 계약서 조항이 소비자(임차인·금융소비자 등)에게 불리한 위험 조항인지 판단하세요.
JSON으로만 답하세요. 다른 텍스트는 출력하지 마세요.

{{"risk_level": "안전 | 주의 | 위험", "reason": "판단 이유 한 문장"}}

[조항]
{clause_text}
"""

LABELS_PATH = Path(__file__).parent.parent / "data" / "real_clause_labels.csv"
_out_name = sys.argv[1] if len(sys.argv) > 1 else "eval_real_labels_naive_baseline.md"
OUT_PATH = Path(__file__).parent.parent / "docs" / _out_name
_splits = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None

_ATTEMPTS = 2


def _load_labels() -> list:
    with open(LABELS_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if _splits:
        rows = [r for r in rows if r["split"] in _splits]
    return rows


def _naive_call(llm, clause_text: str) -> dict:
    prompt = _NAIVE_PROMPT.format(clause_text=clause_text)
    for attempt in range(_ATTEMPTS):
        try:
            raw = llm.invoke(prompt).content
            if isinstance(raw, list):  # anthropic 멀티블록 대응
                raw = "".join(b.get("text", "") for b in raw if isinstance(b, dict))
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            data = json.loads(raw)
            if data.get("risk_level") in ("안전", "주의", "위험"):
                return data
        except Exception as exc:
            if attempt + 1 == _ATTEMPTS:
                print(f"  파싱 실패({exc}) -> parse_fail 처리")
    return {"risk_level": "parse_fail", "reason": ""}


def run_eval() -> list:
    llm = get_worker_llm()
    rows = _load_labels()
    results = []
    for row in rows:
        pred = _naive_call(llm, row["clause_text"])
        results.append({"row": row, "prediction": pred})
        gold = row["gold_risk_level"]
        p = pred["risk_level"]
        match = "O" if (p != "안전") == (gold != "안전") else "X"
        print(f"[{match}] {row['case_id']}: gold={gold} -> pred={p}")
    return results


def _confusion(results: list) -> dict:
    tp = fp = fn = tn = 0
    parse_fail = 0
    for r in results:
        pred_level = r["prediction"]["risk_level"]
        if pred_level == "parse_fail":
            parse_fail += 1
            pred_level = "주의"  # 실패는 보수적으로 '위험 쪽' 판정으로 집계 (본문에 명시)
        gold_risk = r["row"]["gold_risk_level"] != "안전"
        pred_risk = pred_level != "안전"
        if gold_risk and pred_risk:
            tp += 1
        elif gold_risk and not pred_risk:
            fn += 1
        elif not gold_risk and pred_risk:
            fp += 1
        else:
            tn += 1
    n = len(results)
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn, "parse_fail": parse_fail,
        "precision": tp / (tp + fp) if (tp + fp) else None,
        "recall": tp / (tp + fn) if (tp + fn) else None,
        "accuracy": (tp + tn) / n if n else None,
    }


def _row_line(label: str, c: dict) -> str:
    if c["precision"] is None:
        return f"| {label} | {c['tp']} | {c['fp']} | {c['fn']} | {c['tn']} | - | - | - |"
    return (f"| {label} | {c['tp']} | {c['fp']} | {c['fn']} | {c['tn']} | "
            f"{c['precision']:.2f} | {c['recall']:.2f} | {c['accuracy']:.2f} |")


def render_report(results: list) -> str:
    test = [r for r in results if r["row"]["split"] == "test"]
    test_a = [r for r in test if r["row"].get("label_grade") == "A"]
    c_all, c_a = _confusion(test), _confusion(test_a)

    model = os.getenv("MODEL_WORKER", "claude-haiku-4-5")
    lines = [
        "# 나이브 베이스라인 평가 — 지식·검증 없는 단순 LLM 호출 (공식 Test)",
        "",
        f"모델: `{model}` (프로덕션 워커와 동일), temperature=0. 프롬프트: 위험 여부만",
        "묻는 3줄 지시(위 스크립트 `_NAIVE_PROMPT`). 10유형 체계·표준 조항 예외·법 지식·",
        "Pydantic 검증·인용 검사·재시도 전부 없음.",
        "",
        "비교 상대: 파이프라인 확정치(`docs/eval_real_labels_claude_v21_taxonomy.md`) —",
        "Test 40 P 0.73 / R 0.83 / Acc 0.72, A등급 27건 P 0.56 / R 0.90 / Acc 0.70.",
        "",
        f"parse_fail {c_all['parse_fail']}건은 '주의'(위험 쪽)로 보수 집계.",
        "",
        "| 구분 | TP | FP | FN | TN | Precision | Recall | Accuracy |",
        "|---|---|---|---|---|---|---|---|",
        _row_line(f"test 전체 ({len(test)}건)", c_all),
        _row_line(f"test A등급만 ({len(test_a)}건)", c_a),
        "",
        "## 불일치 사례",
        "",
        "| 출처 | 정답 | 예측 | 조항 발췌 |",
        "|---|---|---|---|",
    ]
    for r in test:
        pred_level = r["prediction"]["risk_level"]
        pl = "주의" if pred_level == "parse_fail" else pred_level
        if (r["row"]["gold_risk_level"] != "안전") != (pl != "안전"):
            excerpt = r["row"]["clause_text"][:40].replace("|", "/")
            lines.append(f"| {r['row']['case_id']} | {r['row']['gold_risk_level']} | {pred_level} | {excerpt}... |")
    return "\n".join(lines) + "\n"


def main() -> None:
    results = run_eval()
    report = render_report(results)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
