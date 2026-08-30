import type { ClauseResult } from '../api'

export type RiskLevel = ClauseResult['risk_level']

export const RISK_META: Record<
  RiskLevel,
  { badge: string; dot: string; text: string; label: string }
> = {
  위험: { badge: 'bg-danger-50 text-danger-600', dot: 'bg-danger-500', text: 'text-danger-600', label: '위험' },
  주의: { badge: 'bg-caution-50 text-caution-700', dot: 'bg-caution-500', text: 'text-caution-700', label: '주의' },
  안전: { badge: 'bg-safe-50 text-safe-700', dot: 'bg-safe-500', text: 'text-safe-700', label: '안전' },
}
