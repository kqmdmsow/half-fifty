# 조항 단위 정밀 recall/precision

`data/clause_level_labels.csv`(66개 라벨)와 `parser.split_clauses()`의 clause_id를 직접 매칭한 결과. 문서 단위 근사치(`eval_results_v2.md`)와 달리 TP/FP/FN을 조항 단위로 정확히 센다.

> **모델 안내**: 2026-07-26 Gemini 전환 실험 중 `gemini-flash-lite-latest` 기준으로
> 측정. 이후 팀 리뷰로 Claude가 복원됐으므로 현재 기본값 기준 수치는 아니다.

| 문서 | TP | FP | FN | TN | Precision | Recall |
|---|---|---|---|---|---|---|
| sample_lease_contract.txt | 4 | 0 | 0 | 1 | 1.00 | 1.00 |
| contract_02_finance_loan.txt | 6 | 0 | 0 | 1 | 1.00 | 1.00 |
| contract_03_lease_normal.txt | 0 | 0 | 0 | 7 | - | - |
| contract_04_gym_membership.txt | 4 | 0 | 0 | 3 | 1.00 | 1.00 |
| contract_05_molit_standard.txt | 0 | 2 | 0 | 14 | 0.00 | - |

**전체 합계**: TP=14 FP=2 FN=0 TN=26 | Precision=0.88 Recall=1.00
