import { useMemo, useState } from 'react'
import type { ClauseResult } from '../api'
import { Button, Card, CopyButton, RiskBadge } from '../components/ui'
import { RISK_META, type RiskLevel } from '../data/sample'

type Filter = '전체' | RiskLevel

export function SummaryScreen({
  clauseCount,
  results,
  isSample,
  onSelectClause,
  onDone,
}: {
  clauseCount: number
  results: ClauseResult[]
  isSample: boolean
  onSelectClause: (clauseId: string) => void
  onDone: () => void
}) {
  const [filter, setFilter] = useState<Filter>('전체')

  const counts = useMemo(
    () =>
      results.reduce(
        (acc, result) => {
          acc[result.risk_level] += 1
          return acc
        },
        { 위험: 0, 주의: 0, 안전: 0 } as Record<RiskLevel, number>,
      ),
    [results],
  )

  const filtered = filter === '전체' ? results : results.filter((r) => r.risk_level === filter)
  const needCheck = counts.위험 + counts.주의
  const topRisk = results.find((r) => r.risk_level === '위험')

  const allQuestions = results
    .flatMap((r) => r.check_questions)
    .map((q, i) => `${i + 1}. ${q}`)
    .join('\n')

  return (
    <div className="mx-auto max-w-3xl animate-fade-up px-6 py-12 md:py-16">
      {isSample && (
        <p className="mb-5 rounded-2xl bg-caution-50 px-4 py-3 text-[14px] font-semibold text-caution-700">
          분석 서버에 연결되지 않아 예시 결과를 보여드리고 있어요.
        </p>
      )}

      <p className="text-[14px] font-bold text-brand-600">분석 완료</p>
      <h1 className="mt-2 text-[26px] font-bold leading-snug tracking-[-0.02em] text-ink-900 md:text-[32px]">
        전체 {clauseCount}개 조항 중
        <br />
        <span className={needCheck > 0 ? 'text-danger-500' : 'text-safe-700'}>
          확인이 필요한 조항이 {needCheck}개
        </span>{' '}
        있어요
      </h1>

      {/* 요약 통계 */}
      <div className="mt-7 grid grid-cols-3 gap-2.5">
        <StatCard label="위험" value={counts.위험} tone="danger" />
        <StatCard label="주의" value={counts.주의} tone="caution" />
        <StatCard label="안전" value={counts.안전} tone="safe" />
      </div>

      {/* 최우선 확인 */}
      {topRisk && (
        <button
          type="button"
          onClick={() => onSelectClause(topRisk.clause_id)}
          className="mt-5 flex w-full items-center justify-between gap-4 rounded-3xl bg-danger-50 px-6 py-5 text-left transition-transform hover:-translate-y-0.5"
        >
          <div>
            <p className="text-[13px] font-bold text-danger-600">가장 먼저 확인하세요</p>
            <p className="mt-1 text-[16px] font-bold text-ink-900">{topRisk.risk_type}</p>
            <p className="mt-1 text-[14px] leading-relaxed text-ink-600">{topRisk.explanation}</p>
          </div>
          <span className="shrink-0 text-[18px] text-danger-500">→</span>
        </button>
      )}

      {/* 필터 */}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1.5">
          {(['전체', '위험', '주의', '안전'] as Filter[]).map((item) => {
            const count = item === '전체' ? results.length : counts[item]
            const active = filter === item
            return (
              <button
                key={item}
                type="button"
                onClick={() => setFilter(item)}
                className={`rounded-full px-3.5 py-2 text-[14px] font-semibold transition-colors ${
                  active ? 'bg-ink-900 text-white' : 'bg-ink-50 text-ink-600 hover:bg-ink-100'
                }`}
              >
                {item} {count}
              </button>
            )
          })}
        </div>
        {allQuestions && <CopyButton text={allQuestions}>질문 전체 복사</CopyButton>}
      </div>

      {/* 조항 카드 */}
      <div className="mt-4 space-y-3">
        {filtered.length === 0 ? (
          <Card className="px-6 py-10 text-center text-[14px] text-ink-400">
            해당하는 조항이 없어요.
          </Card>
        ) : (
          filtered.map((result) => (
            <Card
              key={result.clause_id}
              interactive
              onClick={() => onSelectClause(result.clause_id)}
              className="p-6"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[15px] font-bold text-ink-900">
                    {result.risk_type === '해당 없음' ? '표준 조항' : result.risk_type}
                  </p>
                  <p className="mt-1.5 line-clamp-2 text-[14px] leading-relaxed text-ink-400">
                    {result.explanation}
                  </p>
                </div>
                <RiskBadge level={result.risk_level} />
              </div>
              {result.risk_level !== '안전' && (
                <p className="mt-3.5 rounded-xl bg-ink-25 px-4 py-3 text-[13px] leading-relaxed text-ink-600">
                  <span className={`font-bold ${RISK_META[result.risk_level].badge.split(' ')[1]}`}>
                    근거
                  </span>{' '}
                  {result.risk_evidence}
                </p>
              )}
              <p className="mt-3.5 text-[14px] font-bold text-brand-600">자세히 보기 →</p>
            </Card>
          ))
        )}
      </div>

      <div className="mt-9 flex justify-center">
        <Button variant="secondary" onClick={onDone}>
          결과 활용하고 마치기
        </Button>
      </div>
    </div>
  )
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: 'danger' | 'caution' | 'safe'
}) {
  const style = {
    danger: 'bg-danger-50 text-danger-600',
    caution: 'bg-caution-50 text-caution-700',
    safe: 'bg-safe-50 text-safe-700',
  }[tone]

  return (
    <div className={`rounded-2xl px-4 py-4 text-center ${style}`}>
      <p className="text-[26px] font-extrabold leading-none">{value}</p>
      <p className="mt-1.5 text-[13px] font-bold">{label}</p>
    </div>
  )
}
