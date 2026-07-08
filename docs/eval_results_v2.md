# 평가 결과 (Parser v2 + Prompt v2)

`agent/eval.py`로 `data/`의 계약서 5건을 파이프라인에 실행하고 `data/labels.md` 정답과 대조한 결과.

| 문서 | 조항 수 | 위험 리콜(찾음/정답) | 오탐(FP) | 실행시간(초) | 토큰(입력/출력) | Judge 평균 | 재시도 | 주의필요 |
|---|---|---|---|---|---|---|---|---|
| sample_lease_contract.txt | 5 | 4/4 | 0 | 65.2 | 14808/4846 | 4.75 | 0 | False |
| contract_02_finance_loan.txt | 7 | 6/6 | 0 | 73.3 | 20863/6380 | 4.25 | 0 | False |
| contract_03_lease_normal.txt | 7 | - | 0 | 62.2 | 18147/4829 | 3.50 | 0 | False |
| contract_04_gym_membership.txt | 7 | 3/4 | 0 | 65.8 | 19407/5297 | 4.50 | 0 | False |
| contract_05_molit_standard.txt | 16 | - | 1 | 142.1 | 49618/12572 | 4.00 | 0 | False |

**합계**: 실행시간 408.5초, 토큰 122843/33924 (입력/출력)

리콜은 조항 단위 정답 매칭이 아니라 문서별 위험 판정 건수 대 정답 건수의 근사치다 (자세한 내용은 eval.py 상단 주석 참고).
