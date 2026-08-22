> 측정 조건: 조항별 3회 실행 후 risk_level 다수결 / 과반 없음 0건

# 실물 조항 정답지(real_clause_labels.csv) 평가 결과

`data/real_clause_labels.csv`(정부/법원 판정 기반 4건 — hldcc·LBox·AI Hub 자연발생 템플릿)에 대해 `analysis._analyze_clause()`를 직접 호출한 결과. Parser/Persona/Judge 없이 Analysis 로직만 단독 평가.

**중요**: 이 중 4건(광고대행/신발도매/즉시연금2017-17/바로연금보험2018-8, `data/real_labels.md` 출처)은 `docs/clause_level_dataset_and_split.md`에서 이미 Train/Val로 지정된, 프롬프트 튜닝 이력이 있는 데이터다. 이 4건을 섞어서 낸 수치는 공정한 held-out 평가가 아니므로, **아래 'Test 전용(40건)' 표만 공식 베이스라인으로 취급**한다. Train/Val 결과는 참고용으로만 병기.

## Test 전용 (신규 확보 데이터 40건 — 공식 베이스라인)

| 구분 | TP | FP | FN | TN | Precision | Recall | Accuracy |
|---|---|---|---|---|---|---|---|
| test 전체 (40건) | 0 | 0 | 0 | 0 | - | - | - |
| test A등급만 (27건, 정부·법원 판정) | 0 | 0 | 0 | 0 | - | - | - |

A등급은 hldcc·LBox(정부/법원 판정), C등급은 AI Hub(자체 판단) 출처다. "정부 판정 기반이라 신뢰도 높다"는 주장을 인용할 땐 A등급만 뗀 수치를 써야 한다.

## 참고: Train/Val 서브셋 (튜닝 이력 있음, 공식 수치 아님)

| 구분 | TP | FP | FN | TN | Precision | Recall | Accuracy |
|---|---|---|---|---|---|---|---|
| train (3건) | 3 | 0 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| val (1건) | 1 | 0 | 0 | 0 | 1.00 | 1.00 | 1.00 |

## risk_type 혼동행렬 (Test 전용, 정답이 '위험'인 경우만, gold_type -> predicted_type 분포)

| 정답 risk_type | 예측 분포 |
|---|---|

## 불일치 사례 (전체 1건, split 포함)

| 출처 | split | 정답(level/type) | 예측(level/type) | 조항 발췌 |
|---|---|---|---|---|
| 즉시연금_2017-17 | train | 위험/불명확한 수수료·이자 조건 | 주의/일방적 급부·조건 변경 | 생존연금 지급금액은 변동할 수 있으며 최저보증이율 미만으로 지급될 수 있... |
