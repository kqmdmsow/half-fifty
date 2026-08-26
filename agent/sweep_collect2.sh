#!/usr/bin/env bash
# 2차 스윕 (#180) — 1차에서 다루지 못한 도메인·표현을 채운다.
# 1차는 위험 유형 10종의 대표 표현이었고, 여기서는 금융 상품별 표현과
# 안전 표본이 나올 만한 질의(법원이 유효로 판단한 유형)를 넣는다.
set -u
cd "$(dirname "$0")"
PY=./.venv/bin/python

QUERIES=(
  # 금융 상품별 — 우리 골든셋의 금융 도메인이 얇다
  보험약관 보험금지급 면책기간 고지의무위반 계약전알릴의무
  여신거래약정 대출약정 근저당권설정 연대보증 포괄근보증
  신용카드약관 할부거래 리스계약 팩토링
  투자일임 신탁계약 펀드환매 파생상품거래
  # 서비스·구독 — 소비자 계약 전반
  이용약관해지 자동갱신 멤버십환불 위탁판매
  # 안전 표본이 나올 만한 질의 (법원이 유효로 본 유형)
  약관유효 정당한약관 표준약관해석 신의칙위반아님
)

for q in "${QUERIES[@]}"; do
  echo "### $q"
  $PY collect_cases.py --target prec --query "$q" --section 2 --limit 40 2>&1 \
    | grep -E "^조항 후보|판정 후보" || echo "  (수집 0)"
done

# 공정위도 사건명 외 본문 검색으로 더 긁는다
for q in 시정권고 표준약관 부당한특약; do
  echo "### ftc:$q"
  $PY collect_cases.py --target ftc --query "$q" --section 2 --limit 40 2>&1 \
    | grep -E "^조항 후보|판정 후보" || echo "  (수집 0)"
done
