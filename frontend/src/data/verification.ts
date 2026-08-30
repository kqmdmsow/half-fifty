/** 검증 실측 수치 — 화면에 노출하는 신뢰 지표의 단일 출처 (#169).
 *
 * 하드코딩을 금지하는 이유: 이 수치들은 #156(오탐 튜닝)·#157(코퍼스 확대)로
 * 곧 바뀐다. 화면 여러 곳에 흩어 놓으면 갱신이 새고, 기획서와 화면이 다른
 * 숫자를 말하게 된다.
 *
 * 갱신 규칙: 여기 있는 값은 전부 레포에 근거 문서가 있는 실측치만 쓴다.
 * 추정치·목표치를 넣지 말 것 — 심사에서 파고들면 무너진다.
 */

export const VERIFICATION = {
  /** 정부·법원·공정위 판정 기반 골든셋 총 행수.
   *  근거: data/real_clause_labels.csv(44) + _ext(34) + _finance(33) + _sprint3(51) + _sprint4(4) + _sprint5(4) = 170 */
  goldenRows: 170,

  /** 정부·공정위 제정 표준계약서 오탐 벤치마크.
   *  근거: docs/eval_normal_fp_after_174.md — 5문서 94조항에서 '위험' 판정 0건 */
  normalClauses: 94,
  normalDangerFalsePositives: 0,

  /** LLM 채점자(judge) 교차검증에 쓴 모델 패밀리 수.
   *  근거: docs/eval_pairwise_judge_family_round2.md — Claude·Gemini·Solar·DeepSeek */
  judgeFamilies: 4,

  /** A등급(정부·법원이 실제로 판정) 서브셋 리콜.
   *  근거: docs/eval_real_labels_pr156_case37fix_test40.md — 27건 중 FN 0 (2026-08-25,
   *  #156 "외부 법령 참조는 요율 명시 아님" 예외 정밀화 반영 재측정) */
  gradeARecall: 1.0,
} as const
