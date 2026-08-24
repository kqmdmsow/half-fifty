"""페르소나 효과 자동 측정 — 고령층 모드는 정말 쉬운 말을 내는가 (#174).

## 왜 자동 지표부터 만드는가

정석은 사람 대상 사용성 조사다. 그런데 표본을 모으는 데 시간이 걸리고,
그 전까지 "고령층 모드는 쉬운 말로 설명한다"를 근거 없이 쓸 수는 없다.
사람 없이 잴 수 있는 부분을 먼저 고정한다.

**우리가 고령자·외국인인 척하고 테스트하는 것은 검증이 아니다.** 그건
리허설·버그 찾기 용도이고, 수치로 쓰면 안 된다. 그래서 갈래를 나눈다:
① 사람 없이 되는 객관 지표 (이 스크립트)
② 실제 사람 소수 (N을 밝히고 편의표본임을 명시)
③ 역할극 (문서에 쓰지 않음)

## 한계 (반드시 함께 적을 것)

문장이 짧고 전문용어가 적으면 읽기 쉬울 개연성이 높다는 것뿐이다. 실제로
이해했는지는 사람에게 물어야 안다. 이 수치를 "이해도 개선"으로 읽으면 안 된다.

사용법: cd agent && python eval_persona_readability.py [출력.md]
  N_CLAUSES=8   측정할 조항 수 (기본 8)
"""

import os
import sys
from pathlib import Path

from src.nodes.analysis import _analyze_clause
from src.nodes.persona import _adapt
from src.readability import aggregate, jargon_hits

REPO = Path(__file__).parent.parent
OUT = REPO / "docs" / (sys.argv[1] if len(sys.argv) > 1 else "eval_persona_readability.md")
N_CLAUSES = int(os.getenv("N_CLAUSES", "8"))

PERSONAS = ["adult", "senior", "foreigner"]
PERSONA_LABEL = {"adult": "성인(기본)", "senior": "고령층", "foreigner": "외국인"}

# 금융·계약 도메인에서 고르게 뽑은 조항. 판정이 아니라 **설명문의 난이도**를
# 재는 것이므로 위험·안전이 섞여 있어야 한다.
CLAUSES = [
    "제3조(기한의 이익 상실) 을이 이자 지급을 1회라도 지체한 경우 갑은 즉시 대출금 전액의 상환을 청구할 수 있다.",
    "제2조(이자) 이자율은 갑의 내부 사정에 따라 수시로 변경될 수 있다. 변경된 이자율은 갑의 홈페이지 공지로 갈음한다.",
    "제3조(부정사용의 보상) 대여, 양도, 담보제공, 불법대출, 제3자 보관 등으로 인한 부정사용의 경우 카드사는 보상하지 않습니다.",
    "제3조(특약) 당사는 부동산담보신탁계약의 수탁자로서 임대차보증금 반환책임 및 임대부동산의 수선의무 등에 대하여 일체의 책임이 없으며, 임차인은 이에 동의한다.",
    "제7조(환불) 회원권 등록 후에는 어떠한 경우에도 이용료를 환불하지 아니한다.",
    "제6조(계약의 해제) 임차인이 임대인에게 중도금을 지급하기 전까지 임대인은 계약금의 배액을 상환하고 계약을 해제할 수 있다.",
    "제4조(중도상환수수료) 중도상환수수료는 상환원금의 1.5%로 하며, 대출일로부터 3년 경과 시 면제한다.",
    "제2조(본인확인) 등록된 자료와 일치할 경우 이용자를 본인으로 인정하며, 이용자의 고의나 중대한 과실이 있는 경우 금융기관은 책임을 지지 아니합니다.",
]


def main():
    clauses = CLAUSES[:N_CLAUSES]
    print(f"조항 {len(clauses)}건 × 페르소나 {len(PERSONAS)}종")

    # 분석은 한 번만 — 페르소나는 판정을 바꾸지 않고 설명 문체만 바꾼다.
    # 조항마다 다시 분석하면 판정 변동이 난이도 차이로 잘못 읽힌다.
    analyzed = []
    for i, text in enumerate(clauses, 1):
        r = _analyze_clause(f"c{i:02d}", text)
        analyzed.append((text, r))
        print(f"  분석 {i}/{len(clauses)}: {r['risk_level']}")

    by_persona = {}
    for p in PERSONAS:
        texts = []
        for text, r in analyzed:
            adapted, _ = _adapt(dict(r), p, "ko", text)  # type: ignore[arg-type]
            texts.append(adapted["explanation"])
        by_persona[p] = {"texts": texts, "metrics": aggregate(texts)}
        m = by_persona[p]["metrics"]
        print(f"  {PERSONA_LABEL[p]}: 문장당 {m['avg_sentence_chars']:.0f}자, "
              f"전문용어 {m['jargon_count']:.1f}개")

    base = by_persona["adult"]["metrics"]

    def delta(p: str, key: str) -> str:
        v, b = by_persona[p]["metrics"][key], base[key]
        if p == "adult" or not b:
            return "—"
        return f"{(v - b) / b * 100:+.0f}%"

    L = ["# 페르소나 효과 자동 측정 — 고령층 모드는 정말 쉬운 말을 내는가", "",
         f"조항 {len(clauses)}건, 워커 `{os.getenv('MODEL_WORKER', '(기본)')}`. "
         "판정은 한 번만 내고 설명 문체만 페르소나별로 다시 쓴다 — 조항마다 다시 "
         "분석하면 판정 변동이 난이도 차이로 잘못 읽힌다.", "",
         "> **한계.** 이 지표는 이해도를 재지 않는다. 문장이 짧고 전문용어가 적으면 "
         "읽기 쉬울 개연성이 높다는 것뿐이고, 실제로 이해했는지는 사람에게 물어야 "
         "안다. 사람 대상 조사는 별도로 소규모(N을 밝히고 편의표본임을 명시) 진행한다. "
         "우리가 고령자인 척하고 한 테스트는 수치로 쓰지 않는다.", "",
         "| 지표 | 성인(기본) | 고령층 | 변화 | 외국인 | 변화 |",
         "|---|---|---|---|---|---|"]
    rows = [("평균 문장 길이(자)", "avg_sentence_chars", "{:.0f}"),
            ("문장당 어절 수", "avg_words_per_sentence", "{:.1f}"),
            ("설명당 전문용어(개)", "jargon_count", "{:.1f}"),
            ("100자당 전문용어", "jargon_per_100_chars", "{:.2f}"),
            ("전체 글자 수", "chars", "{:.0f}"),
            ("읽기 시간 추정(초)", "read_seconds", "{:.0f}")]
    for label, key, fmt in rows:
        L.append(f"| {label} | {fmt.format(base[key])} | "
                 f"{fmt.format(by_persona['senior']['metrics'][key])} | {delta('senior', key)} | "
                 f"{fmt.format(by_persona['foreigner']['metrics'][key])} | {delta('foreigner', key)} |")

    L += ["", "## 남아 있는 전문용어", "",
          "고령층 설명에 아직 남은 용어다. 여기 있는 말이 많을수록 프롬프트를 더 "
          "다듬어야 한다는 뜻이다.", ""]
    remaining = sorted({w for t in by_persona["senior"]["texts"] for w in jargon_hits(t)})
    L.append(", ".join(f"`{w}`" for w in remaining) if remaining else "없음.")

    L += ["", "## 실제 출력 비교", ""]
    for i, (text, _) in enumerate(zip(clauses, analyzed)):
        L.append(f"### {i + 1}. {text[:40]}…")
        for p in PERSONAS:
            L.append(f"- **{PERSONA_LABEL[p]}**: {by_persona[p]['texts'][i]}")
        L.append("")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"\n저장: {OUT}")


if __name__ == "__main__":
    main()
