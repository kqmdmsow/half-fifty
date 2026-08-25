"""검수 보조 — 심결 근거 서술에서 조항 문구 후보를 뽑는다 (#180).

## 왜 필요한가

`collect_cases.py`가 공정위 심결 297건의 조항 후보를 모았지만 **clause_text가
비어 있다.** 조항 원문이 심결문 원본에서 표로 조판돼 API 응답에서 탈락하기
때문이다. 검수자가 297건의 원문을 하나씩 열어 표에서 문구를 옮겨 적는 것은
자동화 이전과 다를 바 없는 노동이다.

그런데 공정위의 판단 근거 서술 안에는 문제가 된 문구가 인용되거나 풀어 쓰여
있는 경우가 많다. 그것을 뽑아 두면 검수자는 **찾는 대신 확인만** 하면 된다.

## 이 도구가 하지 않는 것

- **clause_text를 채우지 않는다.** `clause_text_candidate` 열에만 쓴다.
- **review_status를 바꾸지 않는다.** 여전히 `미검수`다.
- **지어낸 문장을 통과시키지 않는다.** LLM이 낸 문구가 근거 서술에 글자 그대로
  없으면 폐기하고 그 사실을 기록한다. 검수자가 지어낸 문장을 원문이라 믿고
  넘기면 골든셋이 조용히 오염된다 — 자동화가 만들 수 있는 최악의 사고다.

사용법: cd agent && python review_assist.py <staging.csv> [--limit 50]
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from src.citation_check import locate_quotes
from src.llm import get_worker_llm, invoke_json

PROMPT_PATH = Path(__file__).parent / "src" / "prompts" / "review_assist.txt"
_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
_CONF = ("높음", "보통", "낮음")


def _grounded(text: str, rationale: str) -> bool:
    """LLM이 낸 문구가 근거 서술에 실재하는가.

    공백 차이에 관대한 대조를 쓴다(locate_quotes). 실재하지 않으면 지어낸 것이다.
    """
    if not text or len(text.strip()) < 15:
        return False
    return bool(locate_quotes(f"「{text}」", rationale))


def assist_one(title: str, rationale: str) -> dict:
    llm = get_worker_llm()
    prompt = _PROMPT.replace("{title}", title).replace("{rationale}", rationale)
    try:
        data = invoke_json(llm, prompt)
    except Exception as exc:
        return {"clause_text_candidate": "", "confidence": "",
                "assist_note": f"추출 실패: {type(exc).__name__}"}

    text = (data.get("clause_text") or "").strip()
    conf = data.get("confidence") if data.get("confidence") in _CONF else "낮음"
    note = str(data.get("note") or "").strip()[:200]

    if not text:
        return {"clause_text_candidate": "", "confidence": "",
                "assist_note": note or "근거 서술에 조항 문구 인용 없음"}
    if not _grounded(text, rationale):
        return {"clause_text_candidate": "", "confidence": "",
                "assist_note": "폐기: 제시한 문구가 근거 서술에 없음 (창작 의심)"}
    return {"clause_text_candidate": text[:400], "confidence": conf,
            "assist_note": note}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    path = Path(args.path)
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    targets = [r for r in rows
               if not r.get("clause_text") and not r.get("clause_text_candidate")]
    todo = targets[:args.limit]
    print(f"{path.name}: 전체 {len(rows)}행, 후보 추출 대상 {len(targets)}행, "
          f"이번 실행 {len(todo)}행")

    stats = {"성공": 0, "인용없음": 0, "폐기": 0}
    for i, row in enumerate(todo, 1):
        out = assist_one(row.get("clause_title", ""), row.get("rationale", ""))
        row.update(out)
        if out["clause_text_candidate"]:
            stats["성공"] += 1
            mark = f"[{out['confidence']}]"
        elif out["assist_note"].startswith("폐기"):
            stats["폐기"] += 1
            mark = "[폐기]"
        else:
            stats["인용없음"] += 1
            mark = "[없음]"
        print(f"  {i:3d}/{len(todo)} {mark} {out['clause_text_candidate'][:70]}")

    cols = list(rows[0].keys())
    for c in ("clause_text_candidate", "confidence", "assist_note"):
        if c not in cols:
            cols.append(c)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerows([{c: r.get(c, "") for c in cols}])

    print(f"\n{stats}")
    print(f"저장: {path}")
    print("\n※ clause_text_candidate는 후보다. clause_text는 여전히 비어 있고")
    print("  review_status도 미검수 그대로다. 검수자가 원문과 대조해 확정한다.")


if __name__ == "__main__":
    main()
