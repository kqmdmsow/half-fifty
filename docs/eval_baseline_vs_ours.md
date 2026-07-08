# Baseline vs Ours 비교

착수보고서 <표 6> 성능 검증 시나리오: 단일 LLM 호출(Baseline, 페르소나 적응·재생성 없음) vs 4단계 파이프라인(Ours). 같은 모델(MODEL_WORKER)과 같은 Judge 기준(judge_node)으로 채점해 파이프라인 구조 차이만 비교한다.

| 문서 | Judge 평균 (Ours/Base) | 위험 리콜 (Ours/Base) | 오탐 FP (Ours/Base) | 실행시간초 (Ours/Base) | 토큰 (Ours/Base) |
|---|---|---|---|---|---|
| sample_lease_contract.txt | 4.75 / 4.75 | 4/4 / 4/4 | 0 / 0 | 65.2 / 28.3 | 14808+4846 / 3379+2640 |
| contract_02_finance_loan.txt | 4.25 / 5.00 | 6/6 / 6/6 | 0 / 0 | 73.3 / 34.3 | 20863+6380 / 4877+3624 |
| contract_03_lease_normal.txt | 3.50 / 4.25 | - / - | 0 / 2 | 62.2 / 29.8 | 18147+4829 / 3761+2700 |
| contract_04_gym_membership.txt | 4.50 / 4.50 | 3/4 / 4/4 | 0 / 0 | 65.8 / 32.6 | 19407+5297 / 4118+2987 |
| contract_05_molit_standard.txt | 4.00 / 4.00 | - / - | 1 / 8 | 142.1 / 62.9 | 49618+12572 / 13385+6932 |

## Judge 4 Aspect 상세 (Ours/Base)

| 문서 | clarity | faithfulness | risk_coverage | actionability |
|---|---|---|---|---|
| sample_lease_contract.txt | 5.0/5.0 | 4.0/5.0 | 5.0/4.0 | 5.0/5.0 |
| contract_02_finance_loan.txt | 5.0/5.0 | 4.0/5.0 | 4.0/5.0 | 4.0/5.0 |
| contract_03_lease_normal.txt | 5.0/5.0 | 3.0/4.0 | 2.0/4.0 | 4.0/4.0 |
| contract_04_gym_membership.txt | 5.0/5.0 | 4.0/4.0 | 4.0/4.0 | 5.0/5.0 |
| contract_05_molit_standard.txt | 5.0/5.0 | 4.0/4.0 | 3.0/3.0 | 4.0/4.0 |

리콜/오탐 기준은 eval.py 상단 주석과 동일한 건수 기준 근사치다.
