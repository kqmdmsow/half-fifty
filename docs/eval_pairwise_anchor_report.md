# 정답앵커 쌍 — LLM Judge 선호 판단 검증 결과 (RQ6)

`data/anchor_pairs.json`(10건, 위험 5/안전 5)에 대해 `judge_pairwise.compare_debiased()`를 호출한 결과. A=정답형 출력, B=오답형 출력으로 고정 — winner=A면 LLM이 정답을 선호한 것.

> **모델 안내**: 2026-07-26 Gemini 전환 실험 중 `gemini-flash-lite-latest` 기준으로
> 측정. 이후 팀 리뷰로 Claude가 복원됐으므로 현재 기본값 기준 수치는 아니다.

## 쌍별 상세

| id | 정답 risk_level | clarity | faithfulness | risk_coverage | actionability | 위치편향 의심 |
|---|---|---|---|---|---|---|
| hldcc_20 | 위험 | A | A | A | A | - |
| hldcc_990 | 위험 | A | tie | A | A | 예 |
| hldcc_37 | 위험 | A | A | A | A | - |
| hldcc_36 | 안전 | A | tie | tie | A | 예 |
| hldcc_2398 | 안전 | A | tie | tie | A | 예 |
| lbox_90237_해지조항 | 위험 | A | A | A | A | - |
| lbox_90237_연체료 | 위험 | A | A | A | A | - |
| lbox_5882 | 안전 | A | A | A | A | - |
| lbox_11329 | 안전 | A | A | A | A | - |
| lbox_62108 | 안전 | A | A | A | A | - |

## Aspect별 정답 일치율 (Accuracy vs Ground Truth)

| aspect | 정답 선호 / 판단 건수 (tie 제외) | 정답 일치율 |
|---|---|---|
| clarity | 10/10 | 100% |
| faithfulness | 7/7 | 100% |
| risk_coverage | 8/8 | 100% |
| actionability | 10/10 | 100% |

위치 편향 의심(정방향/역방향 판단 불일치)이 발생한 쌍: 3/10건

**해석 기준**: risk_coverage·faithfulness는 사실 판단이라 정답 일치율이 낮으면 LLM Judge를 곧이곧대로 신뢰할 수 없다는 직접 증거다 (RQ6). clarity는 문체 판단이라 상대적으로 덜 걱정할 항목이다.
