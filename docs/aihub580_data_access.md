# AI Hub 580 데이터 접근 안내 (원본은 git에 없음)

`data/raw/sources_research/aihub580/`(원천 TL/VL JSON 9,000여 개 + 조항 원문이
포함된 정제 CSV·체크포인트)은 **AI Hub 이용정책상 제3자 제공·재배포 금지**라서
저장소에 포함하지 않는다 (public 저장소 게시는 "열람 제공"에 해당, 국외 반출
조항도 저촉). 측정 결과 **집계·요약**(docs/eval_aihub580_full_run*.md,
docs/risk_taxonomy_v2.md)만 저장소에 남긴다.

## 재현 절차

1. https://aihub.or.kr 로그인 → 데이터셋 검색: **"법률, 규정 (판결서, 약관 등)
   텍스트 분석 데이터"(019번)** → 다운로드 신청(무료, 즉시 승인) — 팀원 각자
   자기 계정으로 받을 것 (공유 채널 전달도 약관상 제3자 제공에 해당)
2. 압축 해제 시 파일명 CP949 깨짐: `python` `zipfile`로 cp437→cp949 복원
   (스크립트는 대화 기록 참조, 필요 시 재작성)
3. 라벨링데이터(TL/VL)를 `data/raw/sources_research/aihub580/{TL,VL}/`에 배치
4. 정제: 정제 로직은 `agent/eval_aihub580_full.py`가 읽는
   `aihub580_cleaned.csv` 생성 과정 — 유불리 라벨 의미 추론과 등급(tier) 규칙은
   `docs/related_work_and_new_sources.md`·`docs/eval_aihub580_full_run.md` 참조
5. 측정: `cd agent && python eval_aihub580_full.py --model solar [--subset
   strong --tag vXX]` — 체크포인트로 중단 재개 가능

## 라벨 등급 요약 (재현 검증용)

- strong 1,046행: 공정위 심결 인정 불공정 (준공식 지표로 사용 가능)
- weak/reviewed_mixed: 자체 판단 라벨 (음성 라벨로 사용 금지)
- 전체 10,200행, 고유 조항 5,782건 (중복 43%)
