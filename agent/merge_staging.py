"""수집 후보 통합·균형 리포트 (#180).

여러 질의로 나눠 수집한 staging CSV를 하나로 합치고, **골든셋에 넣기 전에
반드시 봐야 할 두 가지**를 보고한다.

1. **판정 균형.** 위험만 잔뜩 모으면 리콜은 부풀고 정밀도는 못 잰다.
   실제로 공정위 경로만 돌렸을 때 297건 중 295건(99%)이 위험이었다.
2. **검수 우선순위.** 추론으로 판정한 것, 신호가 섞인 것, 조항 문구가 없는 것을
   앞에 세운다. 검수자의 시간은 유한하고, 틀릴 가능성이 큰 것부터 봐야 한다.

사용법: cd agent && python merge_staging.py [--out merged.csv]
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

from collect_cases import is_clause_like

STAGING = Path(__file__).parent.parent / "data" / "staging"

# 검수 우선순위 — 숫자가 작을수록 먼저 본다.
def _priority(row: dict) -> int:
    src = row.get("opinion_source", "")
    if "혼재" in src:
        return 0                       # 판정이 뒤집힐 수 있다
    if "추론" in src:
        return 1                       # 원문 확인 필수
    if not row.get("clause_text") and not row.get("clause_text_candidate"):
        return 2                       # 조항 문구를 사람이 찾아야 한다
    if row.get("confidence") == "낮음":
        return 3
    return 4


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="merged_candidates.csv")
    args = ap.parse_args()

    files = sorted(f for f in STAGING.glob("candidates_*.csv"))
    if not files:
        print("staging에 후보 파일이 없다.")
        return

    rows, cols = [], []
    for f in files:
        for r in csv.DictReader(f.open(encoding="utf-8")):
            r["_source_file"] = f.name
            rows.append(r)
            for c in r:
                if c not in cols:
                    cols.append(c)

    # 이미 수집된 파일에도 조항 여부 검사를 적용한다 — 재수집 없이 정리하기
    # 위해서다. 판례 경로에서만 서술문 조각이 섞이므로 그쪽만 본다.
    dropped = 0
    filtered = []
    for r in rows:
        text = r.get("clause_text", "")
        if text and "prec" in r.get("_source_file", "") and not is_clause_like(text):
            dropped += 1
            continue
        filtered.append(r)
    rows = filtered

    # 같은 조항 문구가 여러 질의에서 잡히는 것을 합친다.
    seen, merged = set(), []
    for r in rows:
        key = (r.get("clause_text") or r.get("clause_text_candidate")
               or r.get("rationale", "")[:200])
        if key in seen:
            continue
        seen.add(key)
        merged.append(r)

    merged.sort(key=_priority)
    out = STAGING / args.out
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in merged:
            w.writerows([{c: r.get(c, "") for c in cols}])

    lv = Counter(r.get("gold_risk_level_candidate") or "(미상)" for r in merged)
    has_text = sum(bool(r.get("clause_text") or r.get("clause_text_candidate"))
                   for r in merged)
    print(f"파일 {len(files)}개 · 서술문 조각 {dropped}행 제외 "
          f"· 중복 제거 후 {len(merged)}행")
    print(f"저장: {out}\n")
    print(f"판정 후보 분포: {dict(lv)}")
    print(f"조항 문구 확보: {has_text}/{len(merged)} "
          f"({has_text / len(merged) * 100:.0f}%)")

    risky = lv.get("위험", 0) + lv.get("주의", 0)
    safe = lv.get("안전", 0)
    if risky and safe / max(risky, 1) < 0.5:
        print(f"\n⚠️ 균형 경고: 위험·주의 {risky} vs 안전 {safe}.")
        print("   이대로 골든셋에 넣으면 리콜은 부풀고 정밀도는 못 잰다.")
        print("   안전 표본을 더 모을 것:")
        print("     python collect_cases.py --target prec --query <검색어> "
              "--section 2 --verdict safe")
        print("   법원까지 갔는데 유효 판정을 받은 조항이 특히 값지다 —")
        print("   '위험해 보이지만 유효한 경계 사례'라 오탐 측정에 직접 쓰인다.")

    print("\n검수 우선순위 상위 (틀릴 가능성이 큰 것부터):")
    for r in merged[:5]:
        text = (r.get("clause_text") or r.get("clause_text_candidate") or "(문구 없음)")
        print(f"  [{r.get('opinion_source', '')[:16]:16s}] "
              f"{(r.get('gold_risk_level_candidate') or '?'):3s} {text[:56]}")


if __name__ == "__main__":
    main()
