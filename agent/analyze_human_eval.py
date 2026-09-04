"""사람 평가(#162) 구글 폼 응답 CSV 집계 스크립트.

사용법:
    python analyze_human_eval.py <구글폼_응답.csv>

입력 CSV는 구글 시트에서 파일 > 다운로드 > CSV로 내보낸 원본 그대로 쓴다.
정답·시스템 판정·페르소나 배치는 이 파일이 직접 유지하지 않고
docs/human_eval_answer_key.md에 박힌 JSON 블록을 그때그때 읽는다 — 두 곳이
따로 놀며 어긋나는 사고를 막기 위함이다.

폼 문항 제목은 반드시 "A-1.", "B-3.", "C-1." 같은 번호를 포함해야 한다(예:
"A-1. 어느 설명이 더 이해하기 쉬운가요?"). 번호가 없으면 응답 CSV의 열 이름이
문항끼리 겹쳐서(구글 폼은 동일 제목 문항을 그대로 중복 헤더로 내보낸다) 이
스크립트가 문항을 구분하지 못한다.

트랙 A(선호 비교 8문항)·트랙 B(판정 일치 7문항)·트랙 C(유용성 2~3문항)·
연령대까지 한 번에 집계한다. 문항 원문은 docs/human_eval_form_questions.md,
집계 방법 설명은 docs/human_eval_analysis_plan.md 참조.
"""

import csv
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ANSWER_KEY_MD = REPO_ROOT / "docs" / "human_eval_answer_key.md"

# 공식수치.md §0·Test 40과 동일 기준: '주의'+'위험' = 양성(위험군)
POSITIVE_LEVELS = {"위험", "주의"}


def load_answer_key():
    text = ANSWER_KEY_MD.read_text(encoding="utf-8")
    m = re.search(r"```json\n(.*?)\n```", text, re.S)
    if not m:
        raise SystemExit(f"{ANSWER_KEY_MD}에서 JSON 블록을 찾지 못했다")
    data = json.loads(m.group(1))
    key_a = {item["n"]: item for item in data["track_a"]}
    key_b = {item["n"]: item for item in data["track_b"]}
    return key_a, key_b


def find_col(headers, *needles):
    for h in headers:
        if all(needle in h for needle in needles):
            return h
    return None


def binom_test_two_sided(k, n, p=0.5):
    """양측 정확 이항검정 p-value. scipy 없이 math.comb로 직접 계산한다."""
    if n == 0:
        return None

    def point_prob(i):
        return math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))

    obs = point_prob(k)
    return sum(point_prob(i) for i in range(n + 1) if point_prob(i) <= obs + 1e-12)


def cohen_kappa(labels_a, labels_b):
    """Cohen's kappa. sklearn 없이 혼동행렬에서 직접 계산한다."""
    assert len(labels_a) == len(labels_b)
    n = len(labels_a)
    if n == 0:
        return None
    categories = sorted(set(labels_a) | set(labels_b))
    idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    matrix = [[0] * k for _ in range(k)]
    for a, b in zip(labels_a, labels_b):
        matrix[idx[a]][idx[b]] += 1
    po = sum(matrix[i][i] for i in range(k)) / n
    row_sums = [sum(matrix[i]) for i in range(k)]
    col_sums = [sum(matrix[i][j] for i in range(k)) for j in range(k)]
    pe = sum(row_sums[i] * col_sums[i] for i in range(k)) / (n * n)
    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def collapse(level):
    return "위험군" if level in POSITIVE_LEVELS else "안전"


def analyze_track_a(rows, headers, key_a):
    print("\n=== 트랙 A — 선호 비교 (senior 버전을 더 이해하기 쉽다고 고른 비율) ===")
    total_senior = total_adult = total_tie = 0
    for n in range(1, 9):
        item = key_a[n]
        col = find_col(headers, f"A-{n}.", "이해하기 쉬운가요")
        if not col:
            print(f"  [경고] A-{n} 열을 못 찾음 — 폼 문항 제목이 안내 문구와 일치하는지 확인")
            continue
        c = Counter()
        for row in rows:
            v = (row.get(col) or "").strip()
            if not v:
                continue
            if v == "A":
                persona = item["persona_a"]
            elif v == "B":
                persona = item["persona_b"]
            else:
                persona = "비슷함"
            c[persona] += 1
        senior, adult, tie = c.get("senior", 0), c.get("adult", 0), c.get("비슷함", 0)
        denom = senior + adult
        line = f"  A-{n} ({item['gold_type']}): senior {senior} / adult {adult} / 비슷함 {tie}"
        if denom:
            p = binom_test_two_sided(senior, denom)
            line += f"  senior선호율={senior/denom:.0%}  p={p:.3f}"
        print(line)
        total_senior += senior
        total_adult += adult
        total_tie += tie

    denom = total_senior + total_adult
    print(f"\n  [전체] senior {total_senior} / adult {total_adult} / 비슷함 {total_tie}"
          f" (총 응답 {total_senior + total_adult + total_tie}건)")
    if denom:
        rate = total_senior / denom
        p = binom_test_two_sided(total_senior, denom)
        verdict = "유의함 (p<0.05)" if p < 0.05 else "유의하지 않음"
        print(f"  선호 일치율(비슷함 제외) = {rate:.1%}   이항검정 p={p:.4f}   {verdict}")
    else:
        print("  응답 없음 — CSV 열 매칭을 확인할 것")


def analyze_track_b(rows, headers, key_b):
    print("\n=== 트랙 B — 판정 일치 ===")
    human_binary_all, system_binary_all, gold_binary_all = [], [], []
    for n in range(1, 8):
        item = key_b[n]
        col = find_col(headers, f"B-{n}.", "위험한가요")
        if not col:
            print(f"  [경고] B-{n} 열을 못 찾음 — 폼 문항 제목이 안내 문구와 일치하는지 확인")
            continue
        gold, system = item["gold_level"], item["system_level"]
        vals = [
            (row.get(col) or "").strip()
            for row in rows
            if (row.get(col) or "").strip() in {"위험", "주의", "안전"}
        ]
        human_binary_all.extend(collapse(v) for v in vals)
        system_binary_all.extend([collapse(system)] * len(vals))
        gold_binary_all.extend([collapse(gold)] * len(vals))
        agree_sys = sum(1 for v in vals if collapse(v) == collapse(system))
        agree_gold = sum(1 for v in vals if collapse(v) == collapse(gold))
        match_mark = "O" if item["match"] else "X"
        print(f"  B-{n} (gold={gold}/시스템={system}, 시스템 채점 {match_mark}):"
              f" 응답 {len(vals)}건 / 사람↔시스템 일치 {agree_sys} / 사람↔gold 일치 {agree_gold}"
              f" / 사람 분포 {dict(Counter(vals))}")

    n_total = len(human_binary_all)
    if not n_total:
        print("  응답 없음 — CSV 열 매칭을 확인할 것")
        return
    human_system_rate = sum(
        1 for h, s in zip(human_binary_all, system_binary_all) if h == s
    ) / n_total
    human_gold_rate = sum(
        1 for h, g in zip(human_binary_all, gold_binary_all) if h == g
    ) / n_total
    system_gold_rate = sum(
        1 for s, g in zip(system_binary_all, gold_binary_all) if s == g
    ) / n_total
    kappa = cohen_kappa(human_binary_all, system_binary_all)
    print(f"\n  [전체, 2단계 합침(주의+위험=양성) 기준, N={n_total}건(응답자×문항)]")
    print(f"  사람↔시스템 일치율 = {human_system_rate:.1%}")
    print(f"  사람↔gold 일치율   = {human_gold_rate:.1%}")
    print(f"  시스템↔gold 일치율 = {system_gold_rate:.1%}  (참고 — 답안 키 기록과 같아야 정상)")
    print(f"  Cohen's kappa(사람 vs 시스템) = {kappa:.3f}" if kappa is not None else "  kappa 계산 불가")


LIKERT_C1 = {
    "전혀 도움 안 됨": 1,
    "별로 도움 안 됨": 2,
    "보통": 3,
    "도움 됨": 4,
    "매우 도움 됨": 5,
}


def analyze_track_c(rows, headers):
    print("\n=== 트랙 C — 유용성/수용성 ===")

    c1_col = find_col(headers, "C-1.", "도움이 될 것 같나요")
    if c1_col:
        vals = [LIKERT_C1[v] for v in (row.get(c1_col, "") for row in rows) if v in LIKERT_C1]
        dist = Counter(vals)
        if vals:
            avg = sum(vals) / len(vals)
            dist_str = ", ".join(f"{k}점:{dist.get(k, 0)}명" for k in range(1, 6))
            print(f"  C-1 (도움될 것 같은가, 1~5점): 평균 {avg:.2f}  N={len(vals)}  분포[{dist_str}]")
        else:
            print("  C-1: 응답 없음")
    else:
        print("  [경고] C-1 열을 못 찾음")

    c2_col = find_col(headers, "C-2.", "추천하시겠어요")
    if c2_col:
        vals = [v for v in (row.get(c2_col, "").strip() for row in rows) if v]
        dist = Counter(vals)
        n = len(vals)
        if n:
            yes_rate = dist.get("예", 0) / n
            print(f"  C-2 (추천 의향): 예 {dist.get('예', 0)} / 아니오 {dist.get('아니오', 0)}"
                  f" / 잘 모르겠음 {dist.get('잘 모르겠음', 0)}  (예 비율 {yes_rate:.1%}, N={n})")
        else:
            print("  C-2: 응답 없음")
    else:
        print("  [경고] C-2 열을 못 찾음")

    c3_col = find_col(headers, "C-3", "유용해 보이는 기능")
    if c3_col:
        vals = [v for v in (row.get(c3_col, "").strip() for row in rows) if v]
        if vals:
            dist = Counter(vals)
            print(f"  C-3 (최유용 기능, 선택 문항 응답률 {len(vals)}/{len(rows)}):")
            for k, cnt in dist.most_common():
                print(f"    {k}: {cnt}")
        else:
            print("  C-3: 응답 없음(선택 문항)")
    else:
        print("  [경고] C-3 열을 못 찾음(선택 문항이라 정상일 수 있음)")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("사용법: python analyze_human_eval.py <구글폼_응답.csv>")
    csv_path = Path(sys.argv[1])
    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []

    print(f"응답 {len(rows)}건 로드 ({csv_path})")
    key_a, key_b = load_answer_key()
    analyze_track_a(rows, headers, key_a)
    analyze_track_b(rows, headers, key_b)
    analyze_track_c(rows, headers)

    age_col = find_col(headers, "연령대")
    if age_col:
        print("\n=== 응답자 연령대 분포 ===")
        for age, cnt in Counter(row.get(age_col, "") for row in rows).most_common():
            print(f"  {age}: {cnt}")


if __name__ == "__main__":
    main()
