# 정답앵커 쌍 — LLM Judge 선호 판단 검증 결과 (RQ6, judge=claude)

`data/anchor_pairs.json`(41건, 위험 24/안전 17)에 대해 `judge_pairwise.compare_debiased()`를 호출한 결과. A=정답형 출력, B=오답형 출력으로 고정 — winner=A면 LLM이 정답을 선호한 것.

> **실행 조건**: judge 모델 `claude-sonnet-4-6`, 쌍마다 debiased 비교(정/역방향 2회 호출)를 **3회 반복** 후 aspect별 다수결로 확정(과반 없으면 tie). 반복 간 판정이 갈린 aspect는 '불안정' 컬럼에 표시 — 단발 채점의 재현성 문제 (docs/reproducibility.md) 통제 목적.

## 쌍별 상세 (다수결 확정 결과)

| id | 정답 risk_level | clarity | faithfulness | risk_coverage | actionability | 불안정 | 위치편향 감지 횟수 |
|---|---|---|---|---|---|---|---|
| hldcc_20 | 위험 | A | tie | A | A | faithfulness | 2 |
| hldcc_990 | 위험 | A | tie | A | A | faithfulness | 2 |
| hldcc_37 | 위험 | A | B | A | A | - | 0 |
| hldcc_36 | 안전 | A | A | A | A | - | 0 |
| hldcc_2398 | 안전 | A | A | A | A | - | 0 |
| lbox_90237_해지조항 | 위험 | A | A | A | A | faithfulness | 1 |
| lbox_90237_연체료 | 위험 | A | A | A | A | - | 0 |
| lbox_5882 | 안전 | A | A | A | A | - | 0 |
| lbox_11329 | 안전 | A | A | A | A | - | 0 |
| lbox_62108 | 안전 | A | A | A | A | - | 0 |
| hldcc_24 | 위험 | A | A | A | A | faithfulness | 1 |
| hldcc_1052 | 안전 | A | A | A | A | - | 0 |
| hldcc_2358 | 안전 | A | A | A | A | - | 0 |
| hldcc_932 | 안전 | A | A | A | A | - | 0 |
| hldcc_1037 | 안전 | A | A | A | A | - | 0 |
| hldcc_23 | 안전 | A | A | A | A | - | 0 |
| hldcc_35 | 안전 | A | A | A | A | - | 0 |
| hldcc_1051 | 안전 | A | A | A | A | - | 0 |
| hldcc_1157 | 안전 | A | A | A | A | - | 0 |
| lbox_2488 | 위험 | A | A | A | A | - | 0 |
| lbox_37441 | 안전 | A | A | A | A | - | 0 |
| lbox_90237_해지 | 위험 | A | A | A | A | - | 0 |
| lbox_90237_유익비 | 위험 | A | A | A | A | - | 0 |
| lbox_90237_화재도난 | 위험 | A | A | A | A | - | 0 |
| lbox_90237_해석권 | 위험 | A | A | A | A | - | 0 |
| lbox_146290 | 안전 | A | A | A | A | - | 0 |
| lbox_116067 | 안전 | A | tie | tie | A | faithfulness, risk_coverage | 2 |
| lbox_78728 | 안전 | A | A | A | A | risk_coverage | 1 |
| aihub_0193_시설비 | 위험 | A | A | A | A | - | 0 |
| aihub_0193_해지 | 위험 | A | A | A | A | - | 0 |
| aihub_0193_이율 | 위험 | A | A | A | A | - | 0 |
| aihub_0193_수선면책 | 위험 | A | A | A | A | - | 0 |
| aihub_0193_위약금 | 위험 | A | A | A | A | - | 0 |
| aihub_0190_해지위약금 | 위험 | A | A | A | A | - | 0 |
| aihub_0190_명도이의금지 | 위험 | A | A | A | A | - | 0 |
| aihub_0190_연체료 | 위험 | A | A | A | A | - | 0 |
| aihub_0079_명도이의 | 위험 | A | A | A | A | - | 0 |
| aihub_0079_원상복구 | 위험 | A | A | A | A | - | 0 |
| aihub_0079_배액손해금 | 위험 | A | A | A | A | - | 0 |
| aihub_0079_상인자격 | 위험 | A | A | A | A | - | 0 |
| aihub_0079_해지즉시명도 | 위험 | A | A | A | A | - | 0 |

## Aspect별 정답 일치율 (Accuracy vs Ground Truth)

| aspect | 정답 선호 / 판단 건수 (tie 제외) | 정답 일치율 | 반복 간 불안정 쌍 수 |
|---|---|---|---|
| clarity | 41/41 | 100% | 0 |
| faithfulness | 37/38 | 97% | 5 |
| risk_coverage | 40/40 | 100% | 2 |
| actionability | 41/41 | 100% | 0 |

위치 편향 의심(정방향/역방향 판단 불일치) 발생: 전체 492회 aspect-판정 중 9회 (2%)

**해석 기준**: risk_coverage·faithfulness는 사실 판단이라 정답 일치율이 낮으면 LLM Judge를 곧이곧대로 신뢰할 수 없다는 직접 증거다 (RQ6). clarity는 문체 판단이라 상대적으로 덜 걱정할 항목이다. judge=claude 결과는 worker와 같은 패밀리라 self-preference bias 가능성이 있으므로, 반드시 judge=gemini 결과와 교차 대조할 것.
