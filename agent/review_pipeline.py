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
import os
import csv
import json
import re
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from collect_cases import is_clause_like
from src.citation_check import locate_quotes
from src.eval_repeat import SystemicFailureDetected
from src.llm import get_worker_llm, invoke_json
from src.schemas import RISK_TYPES

REPO = Path(__file__).parent.parent
STAGING = REPO / "data" / "staging" / "merged_candidates.csv"
OUT_CSV = REPO / "data" / "real_clause_labels_sprint3.csv"
OUT_LOG = REPO / "docs" / "review_sprint3_log.md"
# 검수 이력 장부 (#180 사고 후 추가).
#
# 이게 없으면 재실행할 때마다 **이미 기각한 것을 다시 검수한다.** 3차 실행이
# 크레딧 소진으로 무효가 됐을 때, 무엇을 다시 해야 하고 무엇은 안 해도 되는지
# 알 수 없었던 것이 정확히 이 문제였다. 통과분은 골든셋에 남지만 기각분은
# 아무 데도 남지 않았다.
LEDGER = REPO / "data" / "staging" / "review_ledger.csv"
# 중복 검사 대상. **직전 실행 결과(sprint3)도 포함한다** — 그래야 이어서
# 돌릴 때 이미 통과한 행이 자동 기각으로 걸러져 중복 적재가 생기지 않는다.
GOLDEN = [REPO / "data" / f for f in
          ("real_clause_labels.csv", "real_clause_labels_ext.csv",
           "real_clause_labels_finance.csv", "real_clause_labels_sprint3.csv")]

_PROPOSE = (Path(__file__).parent / "src" / "prompts" / "review_propose.txt"
            ).read_text(encoding="utf-8")
_ADVERSARIAL = (Path(__file__).parent / "src" / "prompts" / "review_adversarial.txt"
                ).read_text(encoding="utf-8")

_REVIEWERS = 3          # 문서에 기록된 검수 에이전트 수와 동일
_REJECT_VOTES = 2       # 3명 중 2명 이상 기각이면 기각
_LEVELS = ("위험", "주의", "안전")

# 검수에 쓸 모델. 크레딧이 없으면 무료 제공자로 갈아탄다.
# 저장소가 이미 쓰던 패턴(eval_normal_fp.py "크레딧 소진 시 무료 워커 대체")과 같다.
_REVIEWER = os.getenv("REVIEW_MODEL", "claude")


def _llm():
    """검수·제안에 쓸 LLM. REVIEW_MODEL=solar면 Upstage로 간다.

    한계를 분명히 해 둔다: 제안자와 검수자가 같은 패밀리면 self-preference가
    생긴다. Claude가 제안하고 Solar가 검수하는 교차 구성이 이상적이지만,
    크레딧이 없으면 양쪽 다 Solar가 되어 그 이점이 사라진다. 그래서 어느
    모델로 검수했는지 행마다 기록해 나중에 재검증할 수 있게 한다.
    """
    if _REVIEWER == "solar":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=os.getenv("MODEL_JUDGE_SOLAR", "solar-pro3"),
                          temperature=0, max_retries=1, timeout=90,
                          base_url="https://api.upstage.ai/v1",
                          api_key=os.getenv("UPSTAGE_API_KEY"))
    return get_worker_llm()


def load_ledger() -> dict:
    """이미 검수한 조항의 판정 기록. {조항키: 판정}."""
    if not LEDGER.exists():
        return {}
    return {r["clause_key"]: r["verdict"]
            for r in csv.DictReader(LEDGER.open(encoding="utf-8"))}


def append_ledger(entries: list) -> None:
    exists = LEDGER.exists()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a" if exists else "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["clause_key", "verdict", "reviewer", "reason"])
        if not exists:
            w.writeheader()
        w.writerows(entries)


def clause_key(text: str) -> str:
    return re.sub(r"\s+", "", text)[:60]

# API 이상 감지 (#180 사고 후 추가).
#
# 크레딧이 소진된 상태로 564건을 돌렸더니 **515건이 전부 BadRequestError였는데
# 로그에는 '기각'으로 기록됐다.** 파이프라인이 실패를 승인으로 처리하지 않은 것은
# 맞지만, API 이상과 진짜 기각을 구분하지 못해 로그가 통째로 오염됐다.
# 진짜 기각 사유 통계도 못 내고, 재실행 시 무엇을 다시 봐야 하는지도 알 수 없다.
#
# 그래서 두 겹으로 막는다.
# ① 사전 점검: 대량 실행 전에 호출 하나로 API가 살아 있는지 본다.
# ② 회로 차단: 연속 실패가 한도를 넘으면 즉시 중단한다.
#    eval_repeat.CONSECUTIVE_FULL_FALLBACK_LIMIT와 같은 사고방식이다.
_CONSECUTIVE_API_FAILURE_LIMIT = 5
_api_failures = {"streak": 0}
_failure_lock = threading.Lock()


def _note_api_result(ok: bool) -> None:
    """API 호출 결과를 누적한다. 연속 실패가 한도를 넘으면 중단시킨다."""
    with _failure_lock:
        if ok:
            _api_failures["streak"] = 0
            return
        _api_failures["streak"] += 1
        if _api_failures["streak"] >= _CONSECUTIVE_API_FAILURE_LIMIT:
            raise SystemicFailureDetected(
                f"API 호출이 연속 {_api_failures['streak']}회 실패했다. "
                f"크레딧 소진·인증·레이트리밋을 확인하라. "
                f"계속 돌리면 실패가 '기각'으로 기록돼 로그가 오염된다.")


def preflight() -> None:
    """대량 실행 전 API 생존 확인. 실패하면 시작하지 않는다."""
    try:
        invoke_json(_llm(), '아래 JSON만 출력하세요: {"ok": true}')
    except Exception as exc:
        raise SystemicFailureDetected(
            f"사전 점검 실패 — API를 쓸 수 없다: {type(exc).__name__}: "
            f"{str(exc)[:200]}") from exc


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
        out = invoke_json(_llm(), prompt)
    except Exception as exc:
        _note_api_result(False)
        return {"proposable": False, "reject_reason": f"제안 실패: {type(exc).__name__}"}
    _note_api_result(True)
    return out


def adversarial_review(proposal: dict, rationale: str) -> dict:
    """독립 검수 에이전트 — 반박을 시도한다."""
    prompt = _fill(_ADVERSARIAL, clause_text=proposal.get("clause_text"),
                   risk_level=proposal.get("risk_level"),
                   risk_type=proposal.get("risk_type"),
                   evidence=proposal.get("evidence"), rationale=rationale)
    try:
        out = invoke_json(_llm(), prompt)
    except Exception as exc:
        _note_api_result(False)
        # 검수 실패는 승인이 아니다. 확인하지 못한 것은 통과시키지 않는다.
        return {"verdict": "기각", "reject_reason": f"검수 실패: {type(exc).__name__}"}
    _note_api_result(True)
    return out


def review_one(row: dict, known: set, ledger: dict) -> dict:
    """후보 1건 -> 판정 결과 dict."""
    out = {"case_no": row.get("case_no", ""), "case_name": row.get("case_name", ""),
           "source_file": row.get("_source_file", "")}

    text = (row.get("clause_text") or row.get("clause_text_candidate") or "").strip()
    if not text:
        return {**out, "verdict": "자동기각", "reason": "축자 원문 부재"}
    key = clause_key(text)
    if key in known:
        return {**out, "verdict": "자동기각", "reason": "기존 골든셋과 중복"}
    # 이미 검수해서 기각한 것을 다시 부르지 않는다. 재실행 비용의 대부분이
    # 여기서 나온다 — 3차 실행이 무효가 됐을 때 이 장부가 없어서 무엇을
    # 다시 해야 하는지 알 수 없었다.
    if key in ledger:
        return {**out, "verdict": "건너뜀", "reason": f"이전 검수 {ledger[key]}"}

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
    ledger = load_ledger()
    if ledger:
        print(f"검수 이력 {len(ledger)}건 — 이미 판정한 조항은 건너뛴다")
    todo = rows[args.offset:args.offset + args.limit]
    print(f"후보 {len(rows)}건 중 {len(todo)}건 검수 "
          f"(검수 에이전트 {_REVIEWERS}명, {_REJECT_VOTES}표 기각 시 탈락)")

    try:
        preflight()
    except SystemicFailureDetected as exc:
        print(f"\n중단: {exc}")
        print("아무것도 기록하지 않았다. 기존 결과 파일과 로그는 그대로다.")
        sys.exit(1)

    results = []
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for i, r in enumerate(pool.map(lambda x: review_one(x, known, ledger), todo), 1):
                results.append(r)
                print(f"  {i:3d}/{len(todo)} [{r['verdict']:5s}] "
                      f"{r.get('clause_text', r.get('reason', ''))[:60]}")
    except SystemicFailureDetected as exc:
        # 여기까지의 결과는 유효하므로 버리지 않고 기록한 뒤 중단한다.
        print(f"\n중단: {exc}")
        print(f"{len(results)}건까지의 결과만 기록한다.")

    # 이번에 실제로 판정한 것만 장부에 남긴다 (건너뜀·API 실패는 제외 —
    # 실패를 기록하면 다음 실행에서 영영 건너뛰게 된다).
    append_ledger([
        {"clause_key": clause_key(r.get("clause_text")
                                  or r.get("_text", "") or r["case_no"]),
         "verdict": r["verdict"], "reviewer": _REVIEWER,
         "reason": r.get("reason", "")[:120]}
        for r in results
        if r["verdict"] in ("승인", "수정승인", "기각")
        and "실패" not in r.get("reason", "")
    ])

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
                    "note": (f"sprint3 {r['verdict']} · 검수 {_REVIEWER} · "
                             f"{r['evidence'][:100]}"),
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
