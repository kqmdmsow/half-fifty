# 통합 참고문헌 (half-fifty 전체)

프로젝트 전 문서에서 인용한 논문·데이터셋·자료의 단일 목록. 주제별 정리,
"활용처"는 우리 저장소의 관련 문서/기능. (보고서 참고문헌 절의 원천)

## 1. LLM-as-a-Judge 설계·검증

| 문헌 | 요지 | 활용처 |
|---|---|---|
| Zheng et al. (2023) "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (NeurIPS D&B) | GPT-4 judge–사람 일치 ~85%, 사람–사람 ~81% | 사람-LLM 일치 비교선 (`human_llm_judge_agreement_design.md` §2) |
| Norman, Rivera & Hughes (2026) "Reliability without Validity" (arXiv:2606.19544) | 판사 간 일치(신뢰도) ≠ 실제 정답(타당도) | RQ6 정답앵커 검증의 존재 이유 (§10.1) |
| Rao & Callison-Burch (2026) "Autorubric" (arXiv:2603.00077) | 앵커 예시·근거 인용 규칙·EMD 지표 | 루브릭 앵커 예시·evidence rule (§10.2) |
| Xu et al. (2026) "Am I More Pointwise or Pairwise?" (arXiv:2602.02219) | pointwise에서도 루브릭 나열 순서가 점수에 영향 | aspect 순서 무작위화 (judge.py) |
| Ye et al. (2023) "FLASK" (ICLR 2024, arXiv:2307.10928) | 분해형(analytic) 평가가 사람 판단과 일치도 높음 | 4-aspect 구조 정당화 (§10.2) |
| "Decomposed Criteria-Based Evaluation" (EMNLP 2025 Industry) | 기준별 분해 평가의 진단 가능성 | 〃 |
| CheckEval/RubricHub 계열 | aspect의 이진 체크리스트 분해 | faithfulness 체크리스트화 보류 옵션 (§10.2(5)) |
| Wang & Blanco (2026, arXiv:2605.30568) / RubricRAG (arXiv:2603.20882) | 인스턴스별(참조 기반) 루브릭 | 정답 라벨 주입 아이디어 → 정답앵커 쌍으로 실현 (§11) |

## 2. 판사 패널·편향 (4패밀리 설계 근거)

| 문헌 | 요지 | 활용처 |
|---|---|---|
| "Nine Judges, Two Effective Votes" (arXiv:2605.29800) | 상관된 오류의 판사는 늘려도 실효 없음 | 패널 다양성 원칙 — 4패밀리·추가 확장 중단 결정 |
| "Play Favorites: Self-Bias in LLM-as-a-Judge" (arXiv:2508.06709) | 같은 패밀리 채점 시 10~25% 과대평가 | Claude 단독 judge의 self-preference 완화 실험 |
| "Judging the Judges: Bias Mitigation Strategies" (arXiv:2604.23178) | 편향 완화 전략 체계 비교 | round2 설계 배경 |
| UDA (arXiv:2508.09724) / "Fairness or Fluency?" (arXiv:2601.13649) | pairwise 편향·보정 | 참고 |
| "A Finite-Calibration Regime Map for LLM Judge Panels" (arXiv:2606.01034) | 패널 보정 이론 | 참고 |
| 실무 가이드: futureagi LLM-judge Best Practices 2026 / orq.ai LLM Juries / Comet LLM Juries | 교차 패밀리·다수결 실무 관행 | 패널 운용 결정 (`eval_pairwise_judge_family_round2.md`) |

## 3. 불공정 조항 탐지·계약 NLP

| 문헌/자원 | 요지 | 활용처 |
|---|---|---|
| Lippi et al. (2019) CLAUDETTE | ToS 불공정 조항 9,414건, 5범주 | 유형 체계 국제 정합(매핑 안건), related work |
| "Are LLMs good enough for unfair ToS?" (arXiv:2409.00077) | LLM 직접 판정 성능 평가 | 접근법 선례 |
| "Text to Trust" (arXiv:2510.22531) | FT vs LoRA 트레이드오프 | 2단 구조(소형 분류기) 실험 아이디어 |
| "Attack on Unfair ToS Clause Detection" (arXiv:2211.15556) | 적대적 트리거 취약성 | 견고성 참고 |
| 독소 조항 분류 딥러닝 모델 (정보과학회논문지 2020, KCI ART002645725) | 국내 독소조항 텍스트 분류 | 국내 선행 — 골든셋 기여 대비 |
| CUAD (2021) | 상업계약 41범주 전문가 주석 | 주석 설계 선례 |
| ContractEval (ACL 2025 NLLP) | 조항 단위 법적 리스크 LLM 벤치마크, laziness 지표 | 가장 근접 연구 — laziness 지표 차용 예정 |
| ContractNLI (2021) / ACORD (arXiv:2501.06582) / LegalBench (2023) / CaseHOLD (arXiv:2104.08671) | 계약 NLI·조항 검색·법률 태스크 | related work |

## 4. 한국 법률 LLM 평가

| 문헌 | 요지 | 활용처 |
|---|---|---|
| KBL (LBox, EMNLP 2024 Findings, github.com/lbox-kr/kbl) | 한국 법률 이해 벤치마크 | 백본 모델 선택 근거, LBox 사용 정당성 |
| KCL (arXiv:2512.24572) | 지식 독립 법률 추론 벤치마크 | 참고 |
| PLawBench (arXiv:2601.16669) | 루브릭 기반 실무 법률 평가 | judge 루브릭 계열 근거 |
| "Legal Issue Tree Rubrics" (arXiv:2512.01020) | 쟁점 트리 루브릭 채점 | 루브릭 고도화 아이디어 |
| LRAGE (arXiv:2504.01840) | 법률 RAG 평가 도구 | RAG 도입 시 평가 프레임 |

## 5. 경제학·실증 (문제 정의와 체크리스트 근거)

| 문헌 | 요지 | 활용처 |
|---|---|---|
| **안선영·이상엽 (2025)** 「전세보증금 미반환 주요요인」 주택금융연구 9(2):47-68 — **원문 PDF 보관** | 수도권 보증 453,122건 이항로짓 — 부채비율≥90% 승산 29.9배 등 | `data/jeonse_risk_reference.json`, 체크리스트 임계값 |
| 오창섭 외 (2024) 전세대출보증 사고 지역·가구 특성 | 서울·인천 보증사고 다중회귀 | 지역 위험 참고 |
| 전세사기 예방 제도 개선방안 (KCI ART003140527) / 전세사기 발생원인·법적 방지 (DBpia NODE11595687) | 법·제도 관점 | related work |
| Marotta-Wurgler "Does Anyone Read the Fine Print?" (J. Legal Studies) | 약관 정독률 극소수 실증 | 문제 정의(공시 실패) |
| Becher "Asymmetric Information in Consumer Contracts" (SSRN 1016010) | 정보 비대칭 시장 실패 | 문제 정의 |
| "Behavioural Economics in Unfair Contract Terms" (J. Consumer Policy 2011) | 공시만으로 해결 불가 | 판정+행동지침 설계 정당화 |
| 탄탄주택협동조합 (2025) 전세사기 피해 회복 모델 — **원문 PDF 보관** | 피해 이후 단계 분석 | 예방 단계 개입 서사 대비 |
| HUG 담보인정비율 인하(2023) 보도 (경향신문) | 부채비율 90% 초과 = 사고금액 ~70% | 임계값 정책 근거 |

## 6. 데이터셋·도구

| 자원 | 내용 | 상태 |
|---|---|---|
| LBox Open (github.com/lbox-kr/lbox-open) | 한국 판례 15만 건 | 필터링 사용 — 골든셋 주 소스 |
| hldcc.or.kr 조정사례 게시판·사례집 3권 | 임대차 분쟁조정 사례 | 수집 완료 (A등급 소스) |
| 금감원 분쟁조정결정례 (fss.or.kr) + 금융분쟁조정 사례집 1권 | 금융 결정례 | 수집 완료 (금융 세트) |
| AI Hub 580 「법률/규정 텍스트 분석」 | 약관 1만+ 유불리 태깅 (공정위 심결 연계) | 확보·정제 — 전량 측정 진행 |
| AI Hub 71834 / 71610 | 계약 서식·기계독해 | 신청 병목 (기존 조사) |
| korean-law-mcp (github.com/chrisryugj/korean-law-mcp) | 법제처 법령·판례 MCP | 법령 인용 검증 기능 후보 |
| 국토부 실거래가 공개 API / HUG 보증사고 통계 / KOSIS | 공공 데이터 | 깡통전세 자동화 로드맵 재료 |
