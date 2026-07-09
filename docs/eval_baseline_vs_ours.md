# Baseline vs Ours 비교

착수보고서 <표 6> 성능 검증 시나리오: 단일 LLM 호출(Baseline, 페르소나 적응·재생성 없음) vs 4단계 파이프라인(Ours). 같은 모델(MODEL_WORKER)과 같은 Judge 기준(judge_node)으로 채점해 파이프라인 구조 차이만 비교한다.

| 문서 | Judge 평균 (Ours/Base) | 위험 리콜 (Ours/Base) | 오탐 FP (Ours/Base) | 실행시간초 (Ours/Base) | 토큰 (Ours/Base) |
|---|---|---|---|---|---|
| sample_lease_contract.txt | 4.75 / 4.50 | 4/4 / 4/4 | 0 / 0 | 58.0 / 26.6 | 14788+4751 / 4040+2376 |
| contract_02_finance_loan.txt | 3.75 / 4.75 | 6/6 / 6/6 | 0 / 0 | 81.8 / 37.0 | 20897+6527 / 5694+3687 |
| contract_03_lease_normal.txt | 3.25 / 3.00 | - / - | 0 / 0 | 192.7 / 21.8 | 53865+14338 / 4034+1853 |
| contract_04_gym_membership.txt | 4.25 / 4.50 | 3/4 / 4/4 | 0 / 0 | 68.1 / 36.7 | 19826+5789 / 5275+3316 |
| contract_05_molit_standard.txt | 4.00 / 3.25 | - / - | 1 / 0 | 153.2 / 52.8 | 49927+12702 / 13062+5697 |

## Judge 4 Aspect 상세 (Ours/Base)

| 문서 | clarity | faithfulness | risk_coverage | actionability |
|---|---|---|---|---|
| sample_lease_contract.txt | 5.0/5.0 | 4.0/4.0 | 5.0/5.0 | 5.0/4.0 |
| contract_02_finance_loan.txt | 4.0/5.0 | 3.0/4.0 | 4.0/5.0 | 4.0/5.0 |
| contract_03_lease_normal.txt | 5.0/5.0 | 3.0/4.0 | 2.0/2.0 | 3.0/1.0 |
| contract_04_gym_membership.txt | 5.0/5.0 | 4.0/4.0 | 4.0/4.0 | 4.0/5.0 |
| contract_05_molit_standard.txt | 5.0/4.0 | 4.0/4.0 | 3.0/2.0 | 4.0/3.0 |

리콜/오탐 기준은 eval.py 상단 주석과 동일한 건수 기준 근사치다.
