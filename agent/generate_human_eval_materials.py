"""사람 평가(#162) 폼 재료 생성 — 조항 선정은 코드에 고정, 설명·판정은 API로 확보.

트랙 A(선호 비교): 골든셋 8조항(위험 6·안전 2, 서로 다른 사건, risk_type 다양화,
[부분축자]/[재구성 인용]/[라벨 품질 보류] 마커 제외)에 대해 adult/senior 설명을
각각 생성하고, 조항마다 A/B 배치를 랜덤화한다(블라인드 — 어느 게 어느 페르소나인지
폼 문항에는 안 남는다).

트랙 B(판정 일치): 골든셋 A등급 7조항(트랙 A와 겹치지 않는 사건)에 대해 현재
시스템 판정(risk_level)을 기록해 정답(gold)·시스템 판정을 답안 키에 남긴다.

Analysis만 실행(Judge 없음). 사전 점검(review_pipeline.preflight)으로 API
생존을 먼저 확인한다.

사용법: cd agent && python generate_human_eval_materials.py
"""

import csv
import json
import random
from pathlib import Path

from review_pipeline import preflight
from src.nodes.analysis import _analyze_clause
from src.nodes.persona import _adapt

REPO = Path(__file__).parent.parent
SEED = 20260831  # 배치 랜덤화 재현성용

# (도메인, case_id) — 사건 독립성·유형 다양성 확인은 선정 과정에서 수작업 검증함
TRACK_A = [
    ("임대차", "20"), ("임대차", "신발도매_2013"), ("임대차", "바로연금보험_2018-8"),
    ("ext", "132494"), ("임대차", "2488"), ("finance", "2015_할부항변배제"),
    ("임대차", "2398"), ("ext", "9838"),
]
TRACK_B = [
    ("임대차", "90237"), ("임대차", "24"), ("임대차", "990"), ("ext", "146502"),
    ("임대차", "35"), ("임대차", "1052"), ("임대차", "36"),
]

FILES = {
    "임대차": REPO / "data" / "real_clause_labels.csv",
    "ext": REPO / "data" / "real_clause_labels_ext.csv",
    "finance": REPO / "data" / "real_clause_labels_finance.csv",
}


def load_rows():
    rows = {}
    for domain, path in FILES.items():
        for r in csv.DictReader(open(path, encoding="utf-8")):
            rows[(domain, r["case_id"])] = r
    return rows


def main():
    print("사전 점검 — API 생존 확인 중...")
    preflight()
    print("API 생존 확인 — 정상. 진행합니다.\n")

    rows = load_rows()
    rng = random.Random(SEED)

    # ── 트랙 A: adult/senior 설명 생성 ──
    track_a_data = []
    for i, (domain, cid) in enumerate(TRACK_A, 1):
        r = rows[(domain, cid)]
        text = r["clause_text"]
        result = _analyze_clause(f"ha_{i:02d}", text)
        adult, _ = _adapt(dict(result), "adult", "ko", text)
        senior, _ = _adapt(dict(result), "senior", "ko", text)

        # A/B 배치 랜덤화 (블라인드) — 절반은 adult=A, 절반은 senior=A
        adult_is_a = rng.random() < 0.5
        slot_a, slot_b = (adult, senior) if adult_is_a else (senior, adult)
        label_a = "adult" if adult_is_a else "senior"
        label_b = "senior" if adult_is_a else "adult"

        track_a_data.append({
            "n": i, "domain": domain, "case_id": cid, "source": r["source"],
            "gold_level": r["gold_risk_level"], "gold_type": r["gold_risk_type"],
            "clause_text": text,
            "explanation_a": slot_a["explanation"], "explanation_b": slot_b["explanation"],
            "persona_a": label_a, "persona_b": label_b,
        })
        print(f"  [트랙A {i}/{len(TRACK_A)}] {domain}/{cid}: 판정={result['risk_level']}/"
              f"{result['risk_type']} (A={label_a}, B={label_b})")

    # ── 트랙 B: 시스템 판정 기록 ──
    track_b_data = []
    for i, (domain, cid) in enumerate(TRACK_B, 1):
        r = rows[(domain, cid)]
        text = r["clause_text"]
        result = _analyze_clause(f"hb_{i:02d}", text)
        match = result["risk_level"] == r["gold_risk_level"] or (
            result["risk_level"] in ("주의", "위험") and r["gold_risk_level"] == "위험"
        )
        track_b_data.append({
            "n": i, "domain": domain, "case_id": cid, "source": r["source"],
            "gold_level": r["gold_risk_level"], "gold_type": r["gold_risk_type"],
            "clause_text": text,
            "system_level": result["risk_level"], "system_type": result["risk_type"],
            "match": match,
        })
        print(f"  [트랙B {i}/{len(TRACK_B)}] {domain}/{cid}: gold={r['gold_risk_level']} "
              f"-> system={result['risk_level']}/{result['risk_type']}")

    # ── 산출물 1: 폼 문항 텍스트 (블라인드) ──
    form_lines = [
        "# 사람 평가 폼 문항 (구글 폼에 복붙용)",
        "",
        "> 이 파일은 평가자에게 그대로 보여줄 문항입니다. 정답·페르소나 라벨은",
        "> `human_eval_answer_key.md`에만 있고 이 파일에는 없습니다(블라인드).",
        "",
        "## 폼 도입부",
        "",
        "> **계약서 조항 설명 평가에 참여해 주세요**",
        ">",
        "> 이 설문은 AI가 만든 계약서 위험 설명을 사람이 어떻게 받아들이는지",
        "> 알아보는 연구용 설문입니다. 소요 시간은 약 5~10분이며, 정답이",
        "> 정해진 문제가 아니니 평소 느끼는 대로 편하게 답해주시면 됩니다.",
        "> 법률 전문가가 아니어도 괜찮습니다 — 오히려 일반인의 직관이",
        "> 저희에게 더 중요합니다. 응답은 익명으로 수집되며 연구 목적",
        "> 외에는 사용하지 않습니다.",
        "",
        "---",
        "",
        "## 트랙 A — 선호 비교 (8문항)",
        "",
        "각 조항마다 설명 두 개(A/B) 중 어느 쪽이 더 이해하기 쉬운지 골라주세요.",
        "",
    ]
    for d in track_a_data:
        form_lines += [
            f"### A-{d['n']}",
            "",
            f"**조항 원문**: \"{d['clause_text']}\"",
            "",
            f"**설명 A**: {d['explanation_a']}",
            "",
            f"**설명 B**: {d['explanation_b']}",
            "",
            "**질문**: 어느 설명이 더 이해하기 쉬운가요?",
            "`○ A   ○ B   ○ 비슷함`",
            "",
            "**(선택) 왜 그렇게 고르셨나요?** — 주관식",
            "",
            "---",
            "",
        ]

    form_lines += [
        "## 트랙 B — 판정 일치 (7문항)",
        "",
        "각 조항이 얼마나 위험하다고 느끼시는지 골라주세요.",
        "",
    ]
    for d in track_b_data:
        form_lines += [
            f"### B-{d['n']}",
            "",
            f"**조항 원문**: \"{d['clause_text']}\"",
            "",
            "**질문**: 이 조항은 얼마나 위험한가요?",
            "`○ 위험   ○ 주의   ○ 안전`",
            "",
            "**(선택) 그렇게 느끼신 이유는?** — 주관식",
            "",
            "---",
            "",
        ]

    form_lines += [
        "## 마무리 — 인적사항 (최소)",
        "",
        "> 마지막으로 몇 가지만 여쭤보겠습니다 (통계 처리용, 개인 식별 안 됨)",
        "",
        "**연령대**: `○ 10대  ○ 20대  ○ 30대  ○ 40대  ○ 50대  ○ 60대 이상`",
        "*(페르소나 연령 매칭 분석용)*",
        "",
        "**(선택) 계약서(임대차 등)를 직접 읽고 서명해본 경험이 있나요?**: "
        "`○ 있음  ○ 없음`",
        "",
        "> 참여해 주셔서 감사합니다.",
    ]
    (REPO / "docs" / "human_eval_form_questions.md").write_text(
        "\n".join(form_lines), encoding="utf-8")

    # ── 산출물 2: 채점 키 (비공개) ──
    key_lines = [
        "# 사람 평가 채점 키 (비공개 — 평가자에게 보여주지 말 것)",
        "",
        "> 정답·시스템 판정·페르소나 배치 라벨. 집계 전용.",
        "",
        "## 트랙 A — 페르소나 배치 정답",
        "",
        "| 문항 | 도메인/case_id | A = | B = | gold |",
        "|---|---|---|---|---|",
    ]
    for d in track_a_data:
        key_lines.append(
            f"| A-{d['n']} | {d['domain']}/{d['case_id']} | **{d['persona_a']}** | "
            f"**{d['persona_b']}** | {d['gold_level']}/{d['gold_type']} |")

    key_lines += [
        "",
        "> 집계: '페르소나 적용(senior) 버전이 선택된 비율'을 계산하려면, 응답의",
        "> A/B 선택을 위 표로 실제 페르소나(adult/senior)로 치환한 뒤 집계한다.",
        "",
        "## 트랙 B — 정답 · 시스템 판정",
        "",
        "| 문항 | 도메인/case_id | gold | 시스템 판정 | 일치 |",
        "|---|---|---|---|---|",
    ]
    for d in track_b_data:
        mark = "O" if d["match"] else "X"
        key_lines.append(
            f"| B-{d['n']} | {d['domain']}/{d['case_id']} | {d['gold_level']}/{d['gold_type']} | "
            f"{d['system_level']}/{d['system_type']} | {mark} |")

    key_lines += [
        "",
        "> 사람 판정 3단계(위험/주의/안전)를 gold 2단계(위험/안전)와 비교할 때는",
        "> '주의'를 어느 쪽에 합칠지 먼저 정한다(권장: 주의+위험=양성, Test 40과",
        "> 동일 기준 — `docs/공식수치.md` §0 참조).",
        "",
        "## 원자료 (감사용)",
        "",
        "```json",
        json.dumps({"track_a": track_a_data, "track_b": track_b_data},
                   ensure_ascii=False, indent=2),
        "```",
    ]
    (REPO / "docs" / "human_eval_answer_key.md").write_text(
        "\n".join(key_lines), encoding="utf-8")

    print(f"\n저장: docs/human_eval_form_questions.md, docs/human_eval_answer_key.md")


if __name__ == "__main__":
    main()
