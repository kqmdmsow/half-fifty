"""검수 파이프라인 — 제작 + 독립 적대적 검수 (#180).

## 이 파이프라인은 검수를 건너뛰지 않는다. 재현한다.

팀이 기존 골든셋 111행을 만들 때 쓴 절차가 문서에 기록돼 있다
(`docs/collection_sprint2_lbox_candidates.md`):

    제작 에이전트가 판결문 전문을 대조해 라벨을 제안
      → **제작자와 독립된 검수 에이전트 3개**가 원문 재대조 + 반박 시도
      → 승인 / 수정승인 / 기각 (실측 생존율 57%)

즉 **팀의 검수는 원래부터 에이전트 기반**이다. 그래서 이 스크립트는 절차를
우회하는 것이 아니라 같은 절차를 같은 규율로 반복한다. 사람 검수를 대체한다고
주장하지 않는다 — 결과물에는 검수 로그가 함께 남고, 최종 반영 여부는 사람이 정한다.

## 왜 적대적으로 검수하는가

검수 에이전트에게 "맞는지 봐 달라"고 하면 대개 맞다고 한다. 그래서 **반박을
시도하라**고 지시하고, 애매하면 기각하도록 편향을 걸었다. 틀린 라벨 하나가
골든셋에 들어가면 그 위에서 잰 모든 수치가 오염된다 — 못 찾는 것보다 잘못
넣는 것이 훨씬 나쁘다.

3개 중 2개 이상이 기각하면 기각한다. 만장일치를 요구하면 통과율이 비현실적으로
낮아지고, 과반만 보면 한 에이전트의 실수가 그대로 통과한다.

## 자동 기각 (LLM 호출 전)

- 조항 원문이 없다 → 축자 원문 부재. 실측 기각 사유 2위다.
- 기존 골든셋과 중복 → 라벨 충돌 위험.
이 둘은 규칙으로 걸러 비용을 아낀다.

사용법:
    cd agent && python review_pipeline.py [--limit 50] [--workers 4]
    결과: data/real_clause_labels_sprint3.csv (통과분)
          docs/review_sprint3_log.md (전건 판정 로그)
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from collect_cases import is_clause_like
from src.citation_check import locate_quotes
from src.llm import get_worker_llm, invoke_json
from src.schemas import RISK_TYPES

REPO = Path(__file__).parent.parent
STAGING = REPO / "data" / "staging" / "merged_candidates.csv"
OUT_CSV = REPO / "data" / "real_clause_labels_sprint3.csv"
OUT_LOG = REPO / "docs" / "review_sprint3_log.md"
GOLDEN = [REPO / "data" / f for f in
          ("real_clause_labels.csv", "real_clause_labels_ext.csv",
           "real_clause_labels_finance.csv")]

_PROPOSE = (Path(__file__).parent / "src" / "prompts" / "review_propose.txt"
            ).read_text(encoding="utf-8")
_ADVERSARIAL = (Path(__file__).parent / "src" / "prompts" / "review_adversarial.txt"
                ).read_text(encoding="utf-8")

_REVIEWERS = 3          # 문서에 기록된 검수 에이전트 수와 동일
_REJECT_VOTES = 2       # 3명 중 2명 이상 기각이면 기각
_LEVELS = ("위험", "주의", "안전")


def _fill(template: str, **kw) -> str:
    for k, v in kw.items():
        template = template.replace("{" + k + "}", str(v or ""))
    return template


def _verbatim(text: str, source: str) -> bool:
    """조항 원문이 자료에 글자 그대로 있는가. 요약·의역은 실패다."""
    return bool(text) and bool(locate_quotes(f"「{text}」", source))


def existing_clause_keys() -> set:
    keys = set()
    for path in GOLDEN:
        if not path.exists():
            continue
        for row in csv.DictReader(path.open(encoding="utf-8")):
            t = re.sub(r"\s+", "", row.get("clause_text", ""))[:60]
            if t:
                keys.add(t)
    return keys


def propose(row: dict) -> dict:
    """제작 에이전트 — 후보에서 라벨을 제안한다."""
    # 이미 확보한 조항 문구를 넘긴다. 판례 경로는 판결문에서 조항을 그대로
    # 뽑아 오는데, 제작 에이전트가 그걸 안 쓰고 rationale에서 다시 추출하면
    # 애써 확보한 원문이 낭비되고 "조항 원문 부재"로 기각된다.
    extracted = (row.get("clause_text") or row.get("clause_text_candidate") or "")
    prompt = _fill(_PROPOSE, case_name=row.get("case_name"), case_no=row.get("case_no"),
                   clause_title=row.get("clause_title"), opinion=row.get("opinion"),
                   articles=row.get("articles"), rationale=row.get("rationale"),
                   extracted=extracted)
    try:
        return invoke_json(get_worker_llm(), prompt)
    except Exception as exc:
        return {"proposable": False, "reject_reason": f"제안 실패: {type(exc).__name__}"}


def adversarial_review(proposal: dict, rationale: str) -> dict:
    """독립 검수 에이전트 — 반박을 시도한다."""
    prompt = _fill(_ADVERSARIAL, clause_text=proposal.get("clause_text"),
                   risk_level=proposal.get("risk_level"),
                   risk_type=proposal.get("risk_type"),
                   evidence=proposal.get("evidence"), rationale=rationale)
    try:
        return invoke_json(get_worker_llm(), prompt)
    except Exception as exc:
        # 검수 실패는 승인이 아니다. 확인하지 못한 것은 통과시키지 않는다.
        return {"verdict": "기각", "reject_reason": f"검수 실패: {type(exc).__name__}"}


def review_one(row: dict, known: set) -> dict:
    """후보 1건 -> 판정 결과 dict."""
    out = {"case_no": row.get("case_no", ""), "case_name": row.get("case_name", ""),
           "source_file": row.get("_source_file", "")}

    text = (row.get("clause_text") or row.get("clause_text_candidate") or "").strip()
    if not text:
        return {**out, "verdict": "자동기각", "reason": "축자 원문 부재"}
    if re.sub(r"\s+", "", text)[:60] in known:
        return {**out, "verdict": "자동기각", "reason": "기존 골든셋과 중복"}

    rationale = row.get("rationale", "")
    p = propose(row)
    if not p.get("proposable"):
        return {**out, "verdict": "기각",
                "reason": p.get("reject_reason") or "조항 유·무효 판단 부재"}

    clause = (p.get("clause_text") or "").strip()
    if not _verbatim(clause, rationale):
        return {**out, "verdict": "기각", "reason": "축자 원문 부재 (제안이 원문과 불일치)"}
    # 원문 대조를 통과해도 **조항이 아닐 수 있다.** 기관이 그 조항을 설명한 말은
    # 근거 서술에 그대로 있으므로 대조를 통과한다("…탈퇴를 상당히 제한하고
    # 있으므로"). 실측 표본 18건 중 3건이 이 유형이었다.
    if not is_clause_like(clause):
        return {**out, "verdict": "기각", "reason": "조항 문언이 아님 (기관의 설명·요약)"}
    if p.get("risk_level") not in _LEVELS:
        return {**out, "verdict": "기각", "reason": f"알 수 없는 판정: {p.get('risk_level')}"}
    rtype = p.get("risk_type") if p.get("risk_type") in RISK_TYPES else "해당 없음"

    votes = [adversarial_review(p, rationale) for _ in range(_REVIEWERS)]
    tally = Counter(v.get("verdict", "기각") for v in votes)
    if tally["기각"] >= _REJECT_VOTES:
        reasons = [v.get("reject_reason", "") for v in votes if v.get("verdict") == "기각"]
        return {**out, "verdict": "기각",
                "reason": next((r for r in reasons if r), "검수단 기각")}

    # 수정승인이 과반이면 검수단이 고친 값을 채택한다.
    fixed = [v for v in votes if v.get("verdict") == "수정승인"]
    if len(fixed) >= _REJECT_VOTES:
        f = fixed[0]
        cand = (f.get("corrected_clause_text") or clause).strip()
        if _verbatim(cand, rationale):
            clause = cand                 # 고친 값도 원문 대조를 통과해야 한다
        if f.get("corrected_risk_level") in _LEVELS:
            p["risk_level"] = f["corrected_risk_level"]
        if f.get("corrected_risk_type") in RISK_TYPES:
            rtype = f["corrected_risk_type"]
        verdict = "수정승인"
    else:
        verdict = "승인"

    return {**out, "verdict": verdict, "reason": "",
            "clause_text": clause, "gold_risk_level": p["risk_level"],
            "gold_risk_type": rtype, "evidence": (p.get("evidence") or "")[:400]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--require-text", action="store_true",
                    help="조항 문구가 있는 후보만 검수한다. merge_staging은 "
                         "'틀릴 가능성이 큰 것 먼저' 순으로 정렬하므로, 그냥 "
                         "앞에서 자르면 문구 없는 후보만 집어 생존율이 왜곡된다.")
    ap.add_argument("--offset", type=int, default=0, help="이어서 돌릴 때 시작 위치")
    args = ap.parse_args()

    rows = list(csv.DictReader(STAGING.open(encoding="utf-8")))
    if args.require_text:
        rows = [r for r in rows
                if (r.get("clause_text") or r.get("clause_text_candidate"))]
    known = existing_clause_keys()
    todo = rows[args.offset:args.offset + args.limit]
    print(f"후보 {len(rows)}건 중 {len(todo)}건 검수 "
          f"(검수 에이전트 {_REVIEWERS}명, {_REJECT_VOTES}표 기각 시 탈락)")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = []
        for i, r in enumerate(pool.map(lambda x: review_one(x, known), todo), 1):
            results.append(r)
            print(f"  {i:3d}/{len(todo)} [{r['verdict']:5s}] "
                  f"{r.get('clause_text', r.get('reason', ''))[:60]}")

    passed = [r for r in results if r["verdict"] in ("승인", "수정승인")]
    tally = Counter(r["verdict"] for r in results)
    rate = len(passed) / len(results) * 100 if results else 0

    if passed:
        cols = ["source", "case_id", "split", "clause_text", "gold_risk_level",
                "gold_risk_type", "label_grade", "note"]
        exists = OUT_CSV.exists()
        with OUT_CSV.open("a" if exists else "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            if not exists:
                w.writeheader()
            for r in passed:
                w.writerow({
                    "source": "법제처 OPEN API/" +
                              ("ftc" if "ftc" in r["source_file"] else "prec"),
                    "case_id": r["case_no"] or r["case_name"][:30],
                    # **test로 자동 배정하지 않는다.** held-out은 사람이 정한다.
                    "split": "train",
                    "clause_text": r["clause_text"],
                    "gold_risk_level": r["gold_risk_level"],
                    "gold_risk_type": r["gold_risk_type"],
                    "label_grade": "A",   # 정부·법원 판정 기반
                    "note": f"sprint3 {r['verdict']} · {r['evidence'][:120]}",
                })

    lines = [f"# 검수 스프린트 3 — {len(results)}건 중 {len(passed)}건 반영",
             "",
             f"> 절차는 `docs/collection_sprint2_lbox_candidates.md`와 동일하다: "
             f"제작 에이전트가 라벨을 제안하고, **제작자와 독립된 검수 에이전트 "
             f"{_REVIEWERS}개**가 원문을 재대조하며 반박을 시도한다. "
             f"{_REJECT_VOTES}표 이상 기각이면 탈락시킨다.",
             "",
             f"**결과: {dict(tally)} · 생존율 {rate:.0f}%** "
             f"(스프린트 2 실측 57%와 비교)", "",
             "> `split`은 전부 `train`으로 넣었다. **held-out 배정은 사람이 정한다** — "
             "자동으로 test에 넣으면 공식 수치의 의미가 사라진다.", "",
             "## 기각 사유 분포", ""]
    reasons = Counter(r["reason"][:40] for r in results if r["verdict"] != "승인" and r.get("reason"))
    lines += [f"- {c}건 — {reason}" for reason, c in reasons.most_common(12)]
    lines += ["", "## 전건 판정", "",
              "| 사건 | 판정 | 조항 / 사유 |", "|---|---|---|"]
    for r in results:
        detail = r.get("clause_text") or r.get("reason", "")
        lines.append(f"| {r['case_no'] or r['case_name'][:24]} | {r['verdict']} | "
                     f"{detail[:80].replace('|', '/')} |")
    OUT_LOG.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n{dict(tally)} · 생존율 {rate:.0f}%")
    print(f"통과분: {OUT_CSV}")
    print(f"로그:   {OUT_LOG}")
    print("\n※ split은 전부 train이다. held-out 배정은 사람이 정한다.")


if __name__ == "__main__":
    main()
