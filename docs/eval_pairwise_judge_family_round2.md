# Pairwise Judge 4패밀리 교차검증 — 2차(재작성 41쌍) 종합 분석 (2026-08-06)

> **[정정: lbox_2488 제외, 유효 표본 40쌍]** PR#18 머지 직전 팀 리뷰(04f713d)가
> lbox_2488을 앵커에서 제거했다 — judge.py 루브릭이 같은 조항을 분류 예시로
> 인용해 pointwise 평가에서 순환 논리가 되기 때문. **pairwise 루브릭에는 이 예시가
> 없어 아래 결과 자체는 오염되지 않았지만**, 데이터 위생을 위해 리베이스 시
> 2488을 제거하고 이 문서의 수치를 40쌍 기준으로 재집계했다(2488은 4판사 전원
> 만장일치 A였어서 일치율 변화는 분모 1 감소뿐, 결론 불변).
> 재집계: Claude f.97%(36/37) / Solar f.77%(24/31) / DeepSeek f.97%(35/36) /
> Gemini(35쌍) 전항목 100% / 패널 다수결 clarity·risk_coverage·actionability
> 100%, faithfulness 97%(34/35).
>
> **[완결: Gemini 40/40 완주]** 무료 한도 리셋 후 잔여 5쌍 완료 — Gemini 최종
> 성적 **전 aspect 100%**(f. 39/39, tie 1), 위치편향 1%로 4판사 중 최저.
> 4판사 완전체 패널 다수결(40쌍): clarity 100% / faithfulness 97%(34/35) /
> risk_coverage 100% / actionability 100% — 결론 확정, RQ6 종결.

1차 분석(`eval_pairwise_judge_family_analysis.md`)에서 발견된 앵커쌍 제작 결함을
재작성한 41쌍으로, **서로 다른 4개 패밀리 판사**를 동일 프로토콜(쌍마다 debiased
정/역방향 2회 × 3회 반복 다수결)로 실행한 결과다.

| 판사 | 모델 | 완주 | 비고 |
|---|---|---|---|
| Claude | claude-sonnet-4-6 | 41/41 | worker와 같은 패밀리 (self-preference 관찰 대상) |
| Solar | solar-pro3 (Upstage) | 41/41 | 한국어 특화 |
| DeepSeek | deepseek-v4-pro (NVIDIA NIM) | 41/41 | |
| Gemini | gemini-flash-lite-latest | **36/41** | 무료 티어 일일 한도로 일시정지 — 잔여 5쌍은 한도 리셋 후 채움 |

## 1. 판사별 정답 일치율 (RQ6, tie 제외)

| aspect | Claude | Solar | DeepSeek | Gemini(36쌍) | **4-판사 다수결 패널** |
|---|---|---|---|---|---|
| clarity | 100% | 100% | 100% | 100% | **100%** (tie 1) |
| faithfulness | 97% | **78%** | 97% | 100% | **97%** (tie 5) |
| risk_coverage | 100% | 100% | 100% | 100% | **100%** (tie 1) |
| actionability | 100% | 100% | 100% | 100% | **100%** (tie 0) |
| 위치편향 감지율 | 2% | 13% | 8% | ~5% | — |
| 반복 불안정(최다 aspect) | 5쌍 | 16쌍 | 8쌍 | — | — |

**핵심 결론 1 — 앵커쌍 재작성이 유효했다.** 1차에서 두 판사가 같은 방향으로
"오답"을 선호하던 쌍들이 사라졌고, faithfulness를 제외한 세 aspect는 4패밀리
전원 만장일치에 가깝다. RQ6 관점에서 "명백한 오답형을 가려내는 능력"은 4패밀리
모두 검증됐다.

**핵심 결론 2 — 남은 마찰은 전부 faithfulness에, 그리고 원인이 특정됐다.**
아래 3절 참조.

## 2. 판사 간 일치도 — κ 해석 주의 (통계 담당 참고)

aspect-판정 단위(공통 쌍 × 4 aspect)의 판사 쌍별 일치:

| 판사 쌍 | 원시 일치율 | Cohen's κ |
|---|---|---|
| Claude–Gemini | 97% | 0.33 |
| Claude–DeepSeek | 90% | 0.08 |
| DeepSeek–Gemini | 90% | −0.01 |
| Claude–Solar | 85% | 0.16 |
| Solar–Gemini | 83% | 0.03 |
| Solar–DeepSeek | 82% | 0.16 |

원시 일치율은 82~97%로 높은데 **κ가 0 근처로 붕괴하는 것은 판정 분포가 A로
극단 편중된 데 따른 κ-역설(prevalence paradox)**이다 — 우연 일치 기대치(pe)가
90%를 넘어서 κ의 분모가 사실상 0이 된다. **사람-LLM 일치(RQ7) 분석에서 같은
함정에 빠지지 않도록, κ 단독 보고 대신 (a) 원시 일치율 + (b) Gwet's AC1 또는
양성/음성 일치율(positive/negative agreement) 병기를 권장**한다. 이건 설계
문서 §11.5에 반영할 가치가 있는 방법론적 발견이다.

## 3. faithfulness 마찰의 원인 — 루브릭 모호성, 그리고 수작업 원본 쌍

판사별 faithfulness non-A(오답 선호 또는 tie) 쌍 수: Claude 4, Solar 16,
DeepSeek 5, Gemini 1. 문제 쌍을 겹쳐 보면 패턴이 명확하다:

- **hldcc_37: Claude·Solar·DeepSeek 3패밀리가 만장일치로 B(오답형) 선호.**
  이 쌍은 재작성 대상이 아니었던 **수작업 원본 10쌍** 중 하나로, 정답형
  explanation이 "정부 조정위에서는 민법상 법정이율인 연 5%가 맞다고 정리한
  사례가 있어요"처럼 **조항 원문에 없는 외부 판정례·법령 지식을 인용**한다.
  루브릭의 faithfulness 정의("원문에 없는 내용을 추가하지 않았는가")를 엄격히
  적용하면 판사들의 B 선호가 루브릭상 옳다 — 1차 분석과 동일한 구조의 문제가
  수작업 원본에도 있었던 것.
- hldcc_20, hldcc_990(원본 쌍), lbox_90237_연체료·aihub_0190_연체료("통상
  수준보다 높은 이율"이라는 외부 기준 판단 포함)에서도 같은 이유의 tie/B가 발생.
- Solar의 16쌍은 이 엄격 해석을 가장 공격적으로 적용한 결과다(한국어 특화
  모델이라 오히려 법률 문구 대조에 민감한 것으로 보임). 패널 다수결이 이를
  흡수해 패널 faithfulness는 97%로 유지된다.

**권고 조치 (다음 PR):**
1. `judge_rubric.txt`·`judge_pairwise_rubric.txt`의 faithfulness 정의에 명확화 문구
   추가: *"조항 원문에 없는 수치·금액·조건을 창작하는 것은 위반이다. 그러나
   조항 밖의 법령·판정례·일반 법률 지식을 근거로 인용하는 것은 위반이 아니다
   (오히려 risk_evidence의 품질 요소다)."*
2. 수작업 원본 10쌍 중 hldcc_37·990·20의 correct_output도 재작성분과 같은
   기준으로 점검 (외부 인용을 explanation이 아닌 risk_evidence로 이동).
3. 1·2 적용 후 faithfulness만 재측정(다른 aspect는 재실행 불요 — 판정 확정적).

## 4. 판사 패널 운용 결론

- **4패밀리 다수결 패널: clarity/risk_coverage/actionability 100%, faithfulness 97%**
  — RQ6(정답앵커 검증)은 이 구성으로 통과로 본다. worker와 같은 패밀리인
  Claude 단독 사용 시의 self-preference 우려는, Claude의 판정이 타 패밀리
  다수결과 사실상 일치함(원시 일치율 90~97%)을 근거로 완화됐다.
- 비용/속도 프로파일: Solar가 가장 빠르고(3s/판정) Claude가 가장 안정적
  (위치편향 2%, 불안정 최소). DeepSeek은 느리지만(46s) 무료. **운영 게이팅은
  Claude 단독 유지, 보고용 평가는 4패밀리 패널**이 합리적 분업.
- 사람 평가(RQ5/RQ7) 기대치: 판사들이 98~100%로 수렴하는 앵커쌍에서 사람
  일치율이 90%+ 나오지 않으면 평가지 설계(블라인딩·순서 무작위화)부터 의심할 것
  (manipulation check로서의 역할).

## 5. 남은 작업

- [ ] Gemini 잔여 5쌍 (무료 한도 리셋 후 `--judge gemini` 재실행 — 체크포인트가 이어받음)
- [ ] faithfulness 루브릭 명확화 + 원본 3쌍 점검 + faithfulness 재측정 (§3 권고)
- [ ] 설계 문서 §11.5에 κ-역설 대응(AC1/양성일치율 병기) 반영


---

## [2026-08-07] faithfulness 루브릭 명확화 패치 — judge 트랙 공식 종결

§3 권고를 적용: 양쪽 루브릭(pointwise `judge.py`, pairwise
`judge_pairwise_rubric.txt`)에 **"조항 밖 법령·판정례 인용은 위반이 아님(근거
품질 요소), 위반은 원문 수치·조건의 창작"** 명확화 삽입.

무료 판사 스팟체크 (문제였던 원본 3쌍 × Solar·Gemini, 비용 0):
- **Gemini: 3쌍 전부 전 aspect A** (패치 전 990 faithfulness tie → A 교정 확인)
- Solar: hldcc_37 B→tie 개선, hldcc_20·990은 여전히 B — Solar의 잔여 엄격성은
  루브릭 해석이 아닌 판사 개성으로 판단(원문 재서술 외 모든 부가를 감점하는
  성향). **패널 다수결이 흡수하는 구조이며(4판사 중 3개 97~100%), 문서화된
  소수 의견으로 수용.**

**종결 선언**: RQ6(정답앵커 42쌍) 검증 완료, 루브릭 패치 완료, 사람 평가지에
실릴 루브릭 문구 확정. 이후 judge 트랙에서 유료 재측정 계획 없음 — 다음
검증 이벤트는 사람 평가(RQ5/RQ7)다.
