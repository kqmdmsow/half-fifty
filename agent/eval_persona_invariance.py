"""페르소나 판정 불변 + 난이도 지표 전체 확대 측정 (요청: #179 4건 -> 골든셋 20+건).

골든셋 라벨 확정분(test split, 라벨 품질 보류 제외)에서 조항을 뽑아:
1. Analysis는 조항당 1회만 실행(판정은 페르소나와 무관하게 고정 — persona._adapt는
   explanation만 재작성하고 risk_level/risk_type/risk_evidence는 dict(result)로
   그대로 복사하므로 구조적으로 불변이다. 이 스크립트는 그 사실을 실측으로도
   재확인한다).
2. adult/senior 페르소나로 explanation만 재작성해 난이도 지표(src/readability.py)를
   비교한다.

사용법: cd agent && python eval_persona_invariance.py [출력.md] [N]
"""

import csv
import sys
from pathlib import Path

from src.nodes.analysis import _analyze_clause
from src.nodes.persona import _adapt
from src.readability import aggregate, measure

REPO = Path(__file__).parent.parent
OUT = REPO / "docs" / (sys.argv[1] if len(sys.argv) > 1 else "eval_persona_invariance.md")
N = int(sys.argv[2]) if len(sys.argv) > 2 else 24

FILES = {
    "임대차": "data/real_clause_labels.csv",
    "ext": "data/real_clause_labels_ext.csv",
    "finance": "data/real_clause_labels_finance.csv",
}


def select_clauses(n: int):
    rows = []
    for domain, path in FILES.items():
        for r in csv.DictReader(open(REPO / path, encoding="utf-8")):
            if r["split"] != "test":
                continue
            if "[라벨 품질 보류" in r["note"]:
                continue
            r["_domain"] = domain
            rows.append(r)

    by_type = {}
    for r in rows:
        key = (r["gold_risk_level"], r["gold_risk_type"])
        by_type.setdefault(key, []).append(r)

    # 위험 유형별로 최대 3건씩, 안전은 유형 다양성 확보 후 남는 예산만큼.
    picked = []
    risk_keys = [k for k in by_type if k[0] == "위험"]
    safe_rows = by_type.get(("안전", "해당 없음"), [])

    for key in risk_keys:
        picked.extend(by_type[key][:3])

    remaining = n - len(picked)
    picked.extend(safe_rows[:max(remaining, 0)])

    return picked[:n]


def main():
    clauses = select_clauses(N)
    print(f"조항 {len(clauses)}건 선정 (위험/안전 혼합, 유형 다양화)")

    analyzed = []
    for i, r in enumerate(clauses, 1):
        result = _analyze_clause(f"pinv_{i:03d}", r["clause_text"])
        analyzed.append((r, result))
        print(f"  [{i}/{len(clauses)}] {r['_domain']}/{r['case_id']}: "
              f"gold={r['gold_risk_level']}/{r['gold_risk_type']} -> "
              f"pred={result['risk_level']}/{result['risk_type']}")

    # ── 판정 불변 검증 ──
    mismatches = []
    adult_texts, senior_texts = [], []
    per_clause = []
    for r, result in analyzed:
        adult, _ = _adapt(dict(result), "adult", "ko", r["clause_text"])
        senior, _ = _adapt(dict(result), "senior", "ko", r["clause_text"])

        invariant = (
            adult["risk_level"] == senior["risk_level"] == result["risk_level"]
            and adult["risk_type"] == senior["risk_type"] == result["risk_type"]
            and adult["risk_evidence"] == senior["risk_evidence"] == result["risk_evidence"]
        )
        if not invariant:
            mismatches.append((r["case_id"], result, adult, senior))

        adult_texts.append(adult["explanation"])
        senior_texts.append(senior["explanation"])

        m_a, m_s = measure(adult["explanation"]), measure(senior["explanation"])
        per_clause.append({
            "case_id": r["case_id"], "domain": r["_domain"],
            "gold_level": r["gold_risk_level"], "gold_type": r["gold_risk_type"],
            "adult_chars": m_a["avg_sentence_chars"], "senior_chars": m_s["avg_sentence_chars"],
            "adult_jargon": m_a["jargon_count"], "senior_jargon": m_s["jargon_count"],
            "adult_text": adult["explanation"], "senior_text": senior["explanation"],
        })

    agg_adult = aggregate(adult_texts)
    agg_senior = aggregate(senior_texts)

    def pct(key):
        b = agg_adult[key]
        if not b:
            return "-"
        return f"{(agg_senior[key] - b) / b * 100:+.0f}%"

    # 역전 케이스: 고령층 문장이 더 길거나 전문용어가 더 많은 경우
    reversals_len = [p for p in per_clause if p["senior_chars"] > p["adult_chars"]]
    reversals_jargon = [p for p in per_clause if p["senior_jargon"] > p["adult_jargon"]]

    lines = [
        "# 페르소나 판정 불변 + 난이도 지표 (골든셋 확대 측정)",
        "",
        f"조항 {len(clauses)}건(골든셋 라벨 확정분 test split, 위험/안전·유형 혼합) x "
        "페르소나 2종(adult/senior). Analysis는 조항당 1회만 실행 — "
        "persona._adapt는 explanation만 재작성하고 risk_level/risk_type/risk_evidence는 "
        "그대로 복사하므로(코드 구조상) 판정은 페르소나와 무관하게 고정된다. "
        "아래는 그 사실을 실측으로 재확인한 결과다.",
        "",
        "## 1. 판정 불변",
        "",
        f"- 측정 조항: {len(clauses)}건",
        f"- 판정 불일치(risk_level/risk_type/risk_evidence 중 하나라도 다름): "
        f"**{len(mismatches)}건**",
    ]
    if mismatches:
        lines.append("")
        lines.append("| case_id | 원본 | adult | senior |")
        lines.append("|---|---|---|---|")
        for cid, orig, adult, senior in mismatches:
            lines.append(f"| {cid} | {orig['risk_level']}/{orig['risk_type']} | "
                         f"{adult['risk_level']}/{adult['risk_type']} | "
                         f"{senior['risk_level']}/{senior['risk_type']} |")
    else:
        lines.append("- 전 조항 판정 완전 일치. 코드 구조(설명만 재작성)와 실측이 일치한다.")

    lines += [
        "",
        "## 2. 난이도 지표 (adult 대비 senior 변화)",
        "",
        "| 지표 | adult(기본) | senior(고령층) | 변화 |",
        "|---|---|---|---|",
        f"| 평균 문장 길이(자) | {agg_adult['avg_sentence_chars']:.0f} | "
        f"{agg_senior['avg_sentence_chars']:.0f} | {pct('avg_sentence_chars')} |",
        f"| 문장당 어절 수 | {agg_adult['avg_words_per_sentence']:.1f} | "
        f"{agg_senior['avg_words_per_sentence']:.1f} | {pct('avg_words_per_sentence')} |",
        f"| 설명당 전문용어(개) | {agg_adult['jargon_count']:.1f} | "
        f"{agg_senior['jargon_count']:.1f} | {pct('jargon_count')} |",
        f"| 100자당 전문용어 | {agg_adult['jargon_per_100_chars']:.2f} | "
        f"{agg_senior['jargon_per_100_chars']:.2f} | {pct('jargon_per_100_chars')} |",
        f"| 전체 글자 수 | {agg_adult['chars']:.0f} | {agg_senior['chars']:.0f} | "
        f"{pct('chars')} |",
        "",
        "> **한계**: 이 지표는 이해도를 재지 않는다. 문장이 짧고 전문용어가 적으면 "
        "읽기 쉬울 개연성이 높다는 것뿐이다 — 실제 이해도는 사람 평가(#162)로 "
        "따로 측정한다.",
        "",
        "## 3. 일관성",
        "",
        f"- 문장 길이 역전(senior가 adult보다 김): **{len(reversals_len)}/{len(clauses)}건**",
        f"- 전문용어 역전(senior가 adult보다 많음): **{len(reversals_jargon)}/{len(clauses)}건**",
    ]
    if reversals_len:
        lines.append("")
        lines.append("### 문장 길이 역전 사례")
        lines.append("| case_id | 유형 | adult(자) | senior(자) |")
        lines.append("|---|---|---|---|")
        for p in reversals_len:
            lines.append(f"| {p['case_id']} | {p['gold_level']}/{p['gold_type']} | "
                         f"{p['adult_chars']:.0f} | {p['senior_chars']:.0f} |")
    if reversals_jargon:
        lines.append("")
        lines.append("### 전문용어 역전 사례")
        lines.append("| case_id | 유형 | adult(개) | senior(개) |")
        lines.append("|---|---|---|---|")
        for p in reversals_jargon:
            lines.append(f"| {p['case_id']} | {p['gold_level']}/{p['gold_type']} | "
                         f"{p['adult_jargon']:.1f} | {p['senior_jargon']:.1f} |")

    lines += ["", "## 4. 조항별 상세", ""]
    for p in per_clause:
        lines.append(f"### {p['domain']}/{p['case_id']} ({p['gold_level']}/{p['gold_type']})")
        lines.append(f"- adult({p['adult_chars']:.0f}자/문장, 전문용어{p['adult_jargon']:.0f}): "
                     f"{p['adult_text']}")
        lines.append(f"- senior({p['senior_chars']:.0f}자/문장, 전문용어{p['senior_jargon']:.0f}): "
                     f"{p['senior_text']}")
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n저장: {OUT}")
    print(f"판정 불일치: {len(mismatches)}건 / 길이역전: {len(reversals_len)}건 / "
          f"전문용어역전: {len(reversals_jargon)}건")


if __name__ == "__main__":
    main()
