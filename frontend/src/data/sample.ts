import type { ClauseResult } from '../api'

// 백엔드 미연결 시 화면 확인용 예시 데이터
export const SAMPLE_RESULTS: ClauseResult[] = [
  {
    clause_id: 'clause_002',
    original_text:
      '제2조(보증금의 반환) 임대인은 계약 종료 후 3개월 이내에 임차인에게 보증금을 반환할 수 있다.',
    explanation:
      '계약이 끝난 뒤에도 임대인이 보증금을 최대 3개월 뒤에 돌려줄 수 있다는 뜻입니다. 세입자는 이 기간 동안 보증금을 바로 받지 못할 수 있습니다.',
    risk_level: '위험',
    risk_type: '보증금 반환 지연',
    risk_evidence: '"계약 종료 후 3개월 이내"라는 표현 때문에 즉시 반환이 보장되지 않습니다.',
    check_questions: [
      '계약 종료일에 보증금을 전액 반환할 수 있나요?',
      '반환이 늦어지면 지연이자는 어떻게 계산하나요?',
    ],
  },
  {
    clause_id: 'clause_special_001',
    original_text: '특약 1. 임차인이 계약을 해지하는 경우 보증금의 30%를 위약금으로 한다.',
    explanation: '계약을 중간에 끝내면 보증금의 큰 금액을 위약금으로 내야 할 수 있습니다.',
    risk_level: '위험',
    risk_type: '과도한 위약금',
    risk_evidence: '"보증금의 30%"는 실제 손해보다 과도할 수 있습니다.',
    check_questions: [
      '실제 손해액을 기준으로 조정할 수 있나요?',
      '정상 해지 사유가 있어도 같은 위약금이 적용되나요?',
    ],
  },
  {
    clause_id: 'clause_005',
    original_text:
      '제5조(계약의 해지) 임대인이 필요하다고 판단하는 경우 계약을 해지할 수 있다.',
    explanation: '해지 사유가 넓게 적혀 있어 상대방 판단만으로 계약이 흔들릴 수 있습니다.',
    risk_level: '주의',
    risk_type: '일방적 계약 해지',
    risk_evidence: '"필요하다고 판단하는 경우"라는 기준이 구체적이지 않습니다.',
    check_questions: ['계약 해지가 가능한 구체적 사유를 적을 수 있나요?'],
  },
  {
    clause_id: 'clause_007',
    original_text:
      '제7조(차임 연체와 해지) 임차인이 2기 이상 차임을 연체하면 임대인은 계약을 해지할 수 있다.',
    explanation: '월세를 두 번 이상 밀리면 계약 해지가 가능하다는 표준적인 내용입니다.',
    risk_level: '안전',
    risk_type: '해당 없음',
    risk_evidence: '2기 이상 차임 연체는 표준계약서에 포함되는 통상적인 해지 사유입니다.',
    check_questions: [],
  },
]

export type RiskLevel = ClauseResult['risk_level']

export const RISK_META: Record<
  RiskLevel,
  { badge: string; dot: string; label: string }
> = {
  위험: { badge: 'bg-danger-50 text-danger-600', dot: 'bg-danger-500', label: '위험' },
  주의: { badge: 'bg-caution-50 text-caution-700', dot: 'bg-caution-500', label: '주의' },
  안전: { badge: 'bg-safe-50 text-safe-700', dot: 'bg-safe-500', label: '안전' },
}
