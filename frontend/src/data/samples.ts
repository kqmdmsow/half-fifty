// 심사용 원클릭 데모 샘플 (#81) — docs/hackathon_finance_ai/데모_시나리오.md 6종.
// 전부 실제 분쟁조정례·판결에서 검수를 거친 조항 (data/real_clause_labels_*.csv 출처).
// 조항 원문은 한국어 유지(분석 대상), 라벨만 i18n (i18n.ts sp1~sp6).

import type { Persona } from '../api'

export interface DemoSample {
  id: string
  labelKey: 'sp1' | 'sp2' | 'sp3' | 'sp4' | 'sp5' | 'sp6'
  /** 예상 판정 — 배지 표시용 (위험 탐지력과 안전 판정 절제력 둘 다 노출) */
  expected: '위험' | '안전'
  text: string
  domain: string
  persona?: Persona
}

export const DEMO_SAMPLES: DemoSample[] = [
  {
    id: 'loan-acceleration',
    labelKey: 'sp1',
    expected: '위험',
    domain: '대출·여신',
    text:
      '채무자에 관하여 다음 각 호의 사유 중 하나라도 발생한 경우에는 회사로부터의 독촉·통지 등이 없어도 채무자는 당연히 회사에 대한 모든 채무의 기한의 이익을 상실하여 곧 이를 갚아야 할 의무를 집니다. 6. 법원으로부터 파산 선고 및 개인 회생 사건의 접수를 통보 받았을 때',
  },
  {
    id: 'insurance-coverage',
    labelKey: 'sp2',
    expected: '안전',
    domain: '보험',
    text:
      '회사는 피보험자가 보험기간 중 진단확정된 질병으로 장애인복지법 시행령의 지체장애 등 장애가 발생하고 1급 또는 2급 장애인이 되었을 때 최초 1회에 한하여 10년간 매년 생활자금을 보험수익자에게 지급합니다',
  },
  {
    id: 'card-liability',
    labelKey: 'sp3',
    expected: '위험',
    domain: '신용카드',
    text: '대여, 양도, 담보제공, 불법대출, 제3자 보관 등으로 인한 부정사용의 경우 카드사는 보상하지 않습니다',
  },
  {
    id: 'efinance-standard',
    labelKey: 'sp4',
    expected: '안전',
    domain: '예금·수신',
    text:
      '자금이체비밀번호, 보안카드 비밀번호 등 등록된 자료와 일치할 경우 서비스 이용자를 본인으로 인정하며, 이용자의 고의나 중대한 과실이 있는 경우 금융기관은 책임을 지지 아니합니다',
  },
  {
    id: 'jeonse-trust',
    labelKey: 'sp5',
    expected: '위험',
    domain: '주택임대차',
    text:
      '당사는 부동산담보신탁계약의 수탁자로서 임대차보증금 반환책임 및 임대부동산의 수선의무 등에 대하여 일체의 책임이 없으며',
  },
  {
    id: 'senior-mode',
    labelKey: 'sp6',
    expected: '위험',
    domain: '대출·여신',
    persona: 'senior',
    text:
      '채무자에 관하여 다음 각 호의 사유 중 하나라도 발생한 경우에는 회사로부터의 독촉·통지 등이 없어도 채무자는 당연히 회사에 대한 모든 채무의 기한의 이익을 상실하여 곧 이를 갚아야 할 의무를 집니다. 6. 법원으로부터 파산 선고 및 개인 회생 사건의 접수를 통보 받았을 때',
  },
]
