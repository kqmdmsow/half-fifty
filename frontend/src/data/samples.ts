// 심사용 원클릭 데모 샘플 (#81) — docs/hackathon_finance_ai/데모_시나리오.md 기반.
// 판정 근거가 되는 핵심 조항은 실제 분쟁조정례·판결 검수 조항 원문 그대로이며
// (data/real_clause_labels_*.csv 출처), 주변에 표준 조항을 더해 실제 계약서
// 형태로 구성했다 — 여러 조항 중 위험을 골라내는 모습까지 데모되도록.
// 파일 샘플 2종(PDF·사진)은 frontend/public/samples/ 정적 자산.

import type { Persona } from '../api'

export interface DemoSample {
  id: string
  labelKey: 'sp1' | 'sp2' | 'sp3' | 'sp4' | 'sp5' | 'sp6' | 'sp7' | 'sp8'
  /** 핵심 확인 포인트의 예상 판정 — 배지 표시용 */
  expected: '위험' | '안전'
  kind: 'text' | 'file'
  domain: string
  persona?: Persona
  text?: string
  fileUrl?: string
  fileName?: string
  fileType?: string
}

const LOAN_TEXT = [
  '제1조(거래조건) 대출금액은 금 20,000,000원, 대출기간은 계약일로부터 36개월로 한다.',
  '제2조(이자) 이자율은 연 5.9%로 하며, 이자는 매월 1일에 후취한다.',
  '제3조(기한 전의 채무변제 의무) 채무자에 관하여 다음 각 호의 사유 중 하나라도 발생한 경우에는 회사로부터의 독촉·통지 등이 없어도 채무자는 당연히 회사에 대한 모든 채무의 기한의 이익을 상실하여 곧 이를 갚아야 할 의무를 집니다. 6. 법원으로부터 파산 선고 및 개인 회생 사건의 접수를 통보 받았을 때',
  '제4조(중도상환수수료) 중도상환수수료는 상환원금의 1.5%로 하며, 대출일로부터 3년 경과 시 면제한다.',
].join('\n')

export const DEMO_SAMPLES: DemoSample[] = [
  {
    id: 'loan-acceleration',
    labelKey: 'sp1',
    expected: '위험',
    kind: 'text',
    domain: '대출·여신',
    text: LOAN_TEXT,
  },
  {
    id: 'insurance-coverage',
    labelKey: 'sp2',
    expected: '안전',
    kind: 'text',
    domain: '보험',
    text: [
      '제1조(보험계약의 성립) 이 계약은 보험계약자의 청약과 회사의 승낙으로 성립합니다.',
      '제2조(보험금의 지급) 회사는 피보험자가 보험기간 중 진단확정된 질병으로 장애인복지법 시행령의 지체장애 등 장애가 발생하고 1급 또는 2급 장애인이 되었을 때 최초 1회에 한하여 10년간 매년 생활자금을 보험수익자에게 지급합니다',
      '제3조(보험료의 납입) 보험계약자는 보험료를 매월 약정한 날짜에 납입하여야 합니다.',
    ].join('\n'),
  },
  {
    id: 'card-liability',
    labelKey: 'sp3',
    expected: '위험',
    kind: 'text',
    domain: '신용카드',
    text: [
      '제1조(카드의 발급) 회사는 회원의 신청에 따라 심사를 거쳐 카드를 발급합니다.',
      '제2조(연회비) 연회비는 카드 종류에 따라 회사가 정한 금액으로 하며, 카드 발급 시 안내합니다.',
      '제3조(부정사용의 보상) 대여, 양도, 담보제공, 불법대출, 제3자 보관 등으로 인한 부정사용의 경우 카드사는 보상하지 않습니다',
      '제4조(이용대금의 결제) 회원은 이용대금을 지정된 결제일에 결제계좌를 통하여 납부합니다.',
    ].join('\n'),
  },
  {
    id: 'efinance-standard',
    labelKey: 'sp4',
    expected: '안전',
    kind: 'text',
    domain: '예금·수신',
    text: [
      '제1조(적용범위) 이 약관은 이용자가 회사가 제공하는 전자금융거래 서비스를 이용함에 있어 적용됩니다.',
      '제2조(본인확인) 자금이체비밀번호, 보안카드 비밀번호 등 등록된 자료와 일치할 경우 서비스 이용자를 본인으로 인정하며, 이용자의 고의나 중대한 과실이 있는 경우 금융기관은 책임을 지지 아니합니다',
      '제3조(이용시간) 서비스 이용시간은 연중무휴 24시간을 원칙으로 하되, 시스템 점검 시 사전 공지 후 중단할 수 있습니다.',
    ].join('\n'),
  },
  {
    id: 'jeonse-trust',
    labelKey: 'sp5',
    expected: '위험',
    kind: 'text',
    domain: '주택임대차',
    text: [
      '제1조(목적) 임대인과 임차인은 아래 표시 주택에 관하여 다음 계약 내용과 같이 임대차계약을 체결한다.',
      '제2조(보증금) 임차인은 보증금 금 150,000,000원을 임대인에게 지급한다.',
      '제3조(특약) 당사는 부동산담보신탁계약의 수탁자로서 임대차보증금 반환책임 및 임대부동산의 수선의무 등에 대하여 일체의 책임이 없으며',
      '제4조(원상회복) 임대차계약이 종료된 경우 임차인은 위 주택을 원상으로 회복하여 임대인에게 반환한다.',
    ].join('\n'),
  },
  {
    id: 'senior-mode',
    labelKey: 'sp6',
    expected: '위험',
    kind: 'text',
    domain: '대출·여신',
    persona: 'senior',
    text: LOAN_TEXT,
  },
  {
    id: 'pdf-standard',
    labelKey: 'sp7',
    expected: '안전',
    kind: 'file',
    domain: '주택임대차',
    fileUrl: '/samples/sample_lease_standard.pdf',
    fileName: '주택임대차표준계약서.pdf',
    fileType: 'application/pdf',
  },
  {
    id: 'photo-ocr',
    labelKey: 'sp8',
    expected: '위험',
    kind: 'file',
    domain: '주택임대차',
    fileUrl: '/samples/sample_lease_photo.jpg',
    fileName: '계약서_사진.jpg',
    fileType: 'image/jpeg',
  },
]
