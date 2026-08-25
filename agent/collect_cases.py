"""공개 심결·판례 자동 수집 (#180) — 골든셋 확충 파이프라인의 앞단.

## 왜 만드는가

골든셋이 111행(조항 라벨)이다. 표본이 작아 공식 Test 40건의 신뢰구간이 ±0.15로
넓고, "법령 참조형 모호 조항" 같은 유형은 train/val에 한 건도 없어서 개선을
시도조차 못 한다(docs/eval_recall_recovery_investigation.md). 데이터가 병목이다.

사람이 판결문을 하나씩 찾아 읽는 방식으로는 규모가 안 나온다. 그런데
**법제처 국가법령정보 공동활용 OPEN API**가 공정거래위원회 결정문·판례·
금융위원회 결정문을 전문까지 무료로 열어 두고 있다. 여기서 후보를 자동으로
긁어오면 사람은 검수에만 집중할 수 있다.

## 이 스크립트가 하지 않는 것 — 중요

**골든셋에 자동으로 넣지 않는다.** 결과는 `data/staging/`에 후보로만 쌓인다.

우리 데이터 원칙은 "원문 정독 → 독립 적대적 검수 통과분만 반영"이고, 3라운드
통과율이 55~60%였다. 자동 수집이 그 절차를 대체하면 골든셋의 신뢰도가
무너지고, 그 위에서 잰 모든 수치가 의미를 잃는다. 자동화가 줄이는 것은
**찾는 수고**이지 **검수**가 아니다.

## 무엇을 얻을 수 있고 무엇은 못 얻는가 (실측)

얻는 것:
- 사건번호·사건명·결정일자 (출처 추적)
- **심사의견: 무효 / 부분 무효 / 유효** — 공정위가 조항별로 내린 판정. 그대로
  gold_risk_level 후보가 된다.
- **약관규제법 조문 인용** — 우리 위험 유형 10종이 애초에 이 조문 체계에서
  나왔으므로 gold_risk_type 후보로 직결된다.
- 판단 근거 서술 (수천 자)

못 얻는 것:
- **"가. 약관조항"의 조항 원문 표.** 결정문 원본에서 표로 조판돼 있어 API의
  XML 응답에서 탈락한다(HTML 형식은 JS 껍데기만 온다). 즉 **조항 원문은
  근거 서술에서 사람이 뽑아내야 한다.** 이것이 이 파이프라인의 한계이고,
  검수 단계가 여전히 필요한 가장 큰 이유다.

사용법:
    cd agent && python collect_cases.py [--limit 50] [--target ftc|prec]
      --limit   가져올 사건 수 (기본 30)
      --target  ftc=공정위 결정문, prec=판례 (기본 ftc)
      --query   검색어 (기본: 사건명 '불공정약관조항')
"""

import argparse
import csv
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).parent.parent
STAGING = REPO / "data" / "staging"
GOLDEN = [REPO / "data" / f for f in
          ("real_clause_labels.csv", "real_clause_labels_ext.csv",
           "real_clause_labels_finance.csv")]

_SEARCH = "https://www.law.go.kr/DRF/lawSearch.do"
_SERVICE = "https://www.law.go.kr/DRF/lawService.do"
# 법제처 OPEN API는 OC(기관 식별자)를 요구하지만 조회 계열은 공개 값으로 동작한다.
# 대량 수집 시에는 open.law.go.kr에서 발급받은 값을 LAW_OC로 넣을 것.
_OC = "test"
_PAUSE = 0.4          # 공공 API에 대한 예의. 초당 3회 미만으로 유지한다.

# 공정위가 조항별로 내리는 판정 → 우리 3단계.
# '부분 무효'를 '주의'로 놓는 것은 보수적 선택이다. 일부라도 무효면 사용자가
# 확인할 이유가 있고, 우리 서비스에서 '안전'은 "확인하지 않아도 된다"는 뜻이다.
_OPINION_TO_LEVEL = {"무효": "위험", "부분 무효": "주의", "부분무효": "주의",
                     "유효": "안전"}

# 약관규제법 조문 → 위험 유형 10종. 우리 유형 체계가 애초에 이 조문에서
# 나왔으므로(docs/risk_taxonomy_v2.md) 매핑이 직접적이다.
# 한 조문이 여러 유형에 걸리는 경우(§6②1 등)는 후보를 나열하고 검수자가 고른다.
_ARTICLE_TO_TYPES = {
    "4": ["권리행사 제한"],
    "6": ["부당한 비용·세금 전가", "선택권 제한·구입 강제", "과도한 위약금"],
    "7": ["책임 면제"],
    "8": ["과도한 위약금"],
    "9": ["일방적 계약 해지", "권리행사 제한", "보증금 반환 지연"],
    "10": ["일방적 급부·조건 변경"],
    "11": ["권리행사 제한"],
    "12": ["일방적 계약 해지"],
    "14": ["권리행사 제한"],
}

# 결정문 형식이 한 가지가 아니다. 실측한 세 가지를 모두 받는다.
#   A) "나. 심사의견 : 무효"
#   B) "2. 심사결과 : 무효"
#   C) 판정 라벨 없이 "…약관법 제9조 제1호에 해당된다"로만 끝남
# C형을 버리면 임대차·헬스장 같은 단일 업체 건이 통째로 날아간다(실측 12건 중 5건).
_CLAUSE_BLOCK = re.compile(r"^\s*(\d{1,2})\.\s*(.{2,40}?조항)\s*$", re.MULTILINE)
_OPINION = re.compile(r"심사(?:의견|결과)\s*[:：]\s*(부분\s*무효|무효|유효)")
_ARTICLE = re.compile(r"약관법\s*제\s*(\d{1,2})\s*조")
# C형 추론용. "해당된다"는 불공정 인정, 부정형은 인정하지 않음이다.
_ARTICLE_HIT = re.compile(r"약관법\s*제\s*\d{1,2}\s*조[^.]{0,40}?해당(?!되지)(?!하지)")
_ARTICLE_MISS = re.compile(r"(해당되지\s*않|해당하지\s*않|부당하다고\s*볼\s*수\s*없|"
                           r"불공정하다고\s*보기는\s*어렵)")


def _get(url: str, params: dict) -> str:
    q = urllib.parse.urlencode({"OC": _OC, "type": "XML", **params})
    with urllib.request.urlopen(f"{url}?{q}", timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def _tag(xml: str, name: str) -> str:
    m = re.search(rf"<{name}\s*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{name}>", xml, re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def _plain(xml: str) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", "\n", xml))
    return re.sub(r"\n{2,}", "\n", re.sub(r"[ \t]+", " ", t)).strip()


def search_cases(target: str, query: str, section: str, limit: int) -> list:
    """사건 목록. (일련번호, 사건명, 사건번호) 튜플."""
    out, page = [], 1
    while len(out) < limit:
        xml = _get(_SEARCH, {"target": target, "search": section,
                             "query": query, "display": 100, "page": page})
        blocks = re.findall(rf"<{target} id=\"\d+\">(.*?)</{target}>", xml, re.S)
        if not blocks:
            break
        for b in blocks:
            seq = _tag(b, "결정문일련번호") or _tag(b, "판례일련번호")
            if seq:
                out.append((seq, _tag(b, "사건명"), _tag(b, "사건번호")))
        page += 1
        time.sleep(_PAUSE)
    return out[:limit]


def _judge_segment(seg: str) -> tuple:
    """구획 하나에서 (판정 문구, 근거 방식)을 뽑는다. 못 찾으면 ("", "")."""
    op = _OPINION.search(seg)
    if op:
        return re.sub(r"\s+", " ", op.group(1)).strip(), "명시"
    # C형: 판정 라벨 없이 조문 인용으로만 결론을 낸다.
    if _ARTICLE_HIT.search(seg):
        return "무효", "조문인용 추론"
    if _ARTICLE_MISS.search(seg) and _ARTICLE.search(seg):
        return "유효", "조문인용 추론"
    return "", ""


def _entry(title: str, seg: str) -> dict:
    opinion, how = _judge_segment(seg)
    arts = sorted(set(_ARTICLE.findall(seg)), key=int)
    types: list = []
    for a in arts:
        for t in _ARTICLE_TO_TYPES.get(a, []):
            if t not in types:
                types.append(t)
    return {
        "clause_title": title,
        "opinion": opinion,
        "opinion_source": how,
        "gold_risk_level_candidate": _OPINION_TO_LEVEL.get(opinion.replace(" ", ""), ""),
        "articles": ",".join(f"제{a}조" for a in arts),
        "gold_risk_type_candidates": "|".join(types),
        "rationale": re.sub(r"\s+", " ", seg)[:1500],
    }


def parse_decision(body: str) -> list:
    """결정문 전문 -> 조항 단위 후보 목록.

    조항 블록마다 판정과 약관법 조문을 뽑는다. 조항 원문 표는 API 응답에
    없으므로 근거 서술을 그대로 담아 검수자가 원문을 찾을 수 있게 한다.

    블록 구분이 없는 단일 조항 결정문(헬스장 환불 건 등)은 문서 전체를
    후보 하나로 낸다 — 쪼개지 못했다고 버리면 그 사건이 통째로 날아간다.
    """
    marks = list(_CLAUSE_BLOCK.finditer(body))
    out = []
    if marks:
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
            e = _entry(m.group(2).strip(), body[m.start():end])
            if e["opinion"]:
                out.append(e)
    if out:
        return out
    e = _entry("(문서 전체 — 조항 구분 없음)", body)
    return [e] if e["opinion"] else []


def existing_case_ids() -> set:
    """이미 골든셋에 있는 사건 식별자. 중복 수집을 막는다."""
    ids = set()
    for path in GOLDEN:
        if not path.exists():
            continue
        for row in csv.DictReader(path.open(encoding="utf-8")):
            for key in ("case_id", "source"):
                v = (row.get(key) or "").strip()
                if v:
                    ids.add(v)
    return ids


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="ftc", choices=["ftc", "prec"])
    ap.add_argument("--query", default="불공정약관조항")
    ap.add_argument("--section", default="1", choices=["1", "2"],
                    help="1=사건명, 2=본문")
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()

    STAGING.mkdir(parents=True, exist_ok=True)
    known = existing_case_ids()
    print(f"골든셋 기존 사건 식별자 {len(known)}개 — 중복은 건너뛴다")

    cases = search_cases(args.target, args.query, args.section, args.limit)
    print(f"검색 결과 {len(cases)}건 (target={args.target}, query={args.query})")

    rows, skipped, no_block, dup_clause = [], 0, 0, 0
    seen_no, seen_sig = set(), set()
    for seq, name, no in cases:
        if no and no in known:
            skipped += 1
            continue
        # 같은 결정문이 피심인 수만큼 중복 등재된다(6개 사업자 건 = 6행).
        # 사건번호가 같으면 같은 문서이므로 한 번만 가져온다.
        if no and no in seen_no:
            skipped += 1
            continue
        if no:
            seen_no.add(no)
        try:
            doc = _get(_SERVICE, {"target": args.target, "ID": seq})
        except Exception as exc:
            print(f"  [실패] {seq}: {type(exc).__name__}")
            continue
        body = _plain(doc)
        found = parse_decision(body)
        if not found:
            no_block += 1
        # 내용 기준 중복 제거. 같은 심결이 피심인 수만큼 별개 사건번호로
        # 등재되는 경우가 있다(6개 사업자 건 = 사건번호 6개, 본문 동일).
        # 사건번호로는 못 걸러지므로 조항 제목+판정+근거로 서명을 만든다.
        # 서명이 짧으면(200자) 같은 문서의 다른 조항까지 뭉개진다 — 실측에서
        # 182건 중 157건이 잘못 제거됐다. 800자로 늘려 정밀도를 확보한다.
        fresh = []
        for c in found:
            sig = (c["clause_title"], c["opinion"], c["rationale"][:800])
            if sig in seen_sig:
                dup_clause += 1
                continue
            seen_sig.add(sig)
            fresh.append(c)
        found = fresh
        for c in found:
            rows.append({
                "source": f"법제처 OPEN API/{args.target}",
                "case_seq": seq, "case_no": no, "case_name": name,
                "doc_url": f"{_SERVICE}?OC={_OC}&target={args.target}&ID={seq}&type=HTML",
                **c,
                "clause_text": "",          # 원문 표는 API에 없다 — 검수자가 채운다
                "review_status": "미검수",
            })
        print(f"  {no or seq}: 조항 후보 {len(found)}건  {name[:40]}")
        time.sleep(_PAUSE)

    if not rows:
        print("\n수집된 후보가 없다.")
        return

    out = STAGING / f"candidates_{args.target}_{args.query}.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    lv = {}
    for r in rows:
        lv[r["gold_risk_level_candidate"] or "(미상)"] = \
            lv.get(r["gold_risk_level_candidate"] or "(미상)", 0) + 1
    print(f"\n조항 후보 {len(rows)}건 저장: {out}")
    print(f"  판정 후보 분포: {lv}")
    print(f"  사건 중복 건너뜀 {skipped}건 · 조항 중복 제거 {dup_clause}건 "
          f"· 조항 블록 미검출 {no_block}건")
    print("\n※ 이 파일은 후보일 뿐 골든셋이 아니다. clause_text가 비어 있고")
    print("  review_status=미검수다. 원문 정독과 독립 적대적 검수를 거친 것만")
    print("  data/real_clause_labels*.csv 로 옮긴다.")


if __name__ == "__main__":
    main()
