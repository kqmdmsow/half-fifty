import { useEffect, useMemo, useState } from 'react'
import type { ClauseResult } from '../api'
import { Button, Card, CopyButton, RiskBadge } from '../components/ui'
import { RISK_META, type RiskLevel } from '../data/sample'
import { riskLevelLabel, riskTypeLabel, t, type LangCode } from '../i18n'
import { clauseHeading } from '../clauseTitle'
import { JeonseCalculator } from '../components/JeonseCalculator'
import { JeonseTimeline } from '../components/JeonseTimeline'
import { speak, stopSpeaking } from '../tts'
import { FormattedText } from '../components/FormattedText'

type Filter = '전체' | RiskLevel

export function SummaryScreen({
  clauseCount,
  results,
  language = 'ko',
  liveProgress = null,
  retrying = false,
  recordSaved = false,
  onSaveRecord,
  domain = '',
  warnings = [],
  onSelectClause,
  onDone,
}: {
  clauseCount: number
  results: ClauseResult[]
  language?: LangCode
  /** 스트리밍 분석 중이면 {done,total} — 완료 조항부터 이 화면에 바로 쌓인다 */
  liveProgress?: { done: number; total: number } | null
  retrying?: boolean
  recordSaved?: boolean
  onSaveRecord?: () => void
  domain?: string
  warnings?: string[]
  onSelectClause: (clauseId: string) => void
  onDone: () => void
}) {
  const [filter, setFilter] = useState<Filter>('전체')
  const [reading, setReading] = useState(false)

  // 화면을 떠나면 낭독도 멈춘다
  useEffect(() => () => stopSpeaking(), [])
  const live = Boolean(liveProgress)

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
      {warnings.map((warning) => (
        <p
          key={warning}
          className="mb-5 rounded-2xl bg-caution-50 px-4 py-3 text-[14px] font-semibold text-caution-700"
        >
          ⚠️ {warning}
        </p>
      ))}

      {live && liveProgress ? (
        <div className="flex items-center gap-2.5">
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-brand-200 border-t-brand-500" />
          <p className="text-[14px] font-bold text-brand-600">
            {t(language, 'analyzingLive', { done: liveProgress.done, total: liveProgress.total })}{' '}
            <span className="font-semibold text-ink-400">— {t(language, 'liveHint')}</span>
          </p>
        </div>
      ) : (
        <p className="text-[14px] font-bold text-brand-600">{t(language, 'analysisDone')}</p>
      )}

      <h1 className="mt-2 text-[26px] font-bold leading-snug tracking-[-0.02em] text-ink-900 md:text-[32px]">
        {t(language, 'headlineTotal', { total: clauseCount })}
        <br />
        <span className={needCheck > 0 ? 'text-danger-500' : 'text-safe-700'}>
          {t(language, 'headlineNeed', { need: needCheck })}
        </span>
      </h1>

      {/* 검증 대기 고지 — 조항은 다 나왔지만 judge 확정 전.
          재시도 중에는 카드가 교체되는 이유를 명시한다 (#101) */}
      {live && retrying ? (
        <p className="mt-4 rounded-2xl bg-caution-50 px-4 py-3 text-[13px] font-semibold text-caution-700">
          🔄 {t(language, 'retryNote')}
        </p>
      ) : live && liveProgress && liveProgress.done >= liveProgress.total && liveProgress.total > 0 ? (
        <p className="mt-4 rounded-2xl bg-brand-50 px-4 py-3 text-[13px] font-semibold text-brand-600">
          🛡️ {t(language, 'verifyingNote')}
        </p>
      ) : null}

      {/* 요약 통계 */}
      <div className="mt-7 grid grid-cols-3 gap-2.5">
        <StatCard label={riskLevelLabel(language, '위험')} value={counts.위험} tone="danger" />
        <StatCard label={riskLevelLabel(language, '주의')} value={counts.주의} tone="caution" />
        <StatCard label={riskLevelLabel(language, '안전')} value={counts.안전} tone="safe" />
      </div>

      {/* 최우선 확인 */}
      {topRisk && (
        <button
          type="button"
          onClick={() => onSelectClause(topRisk.clause_id)}
          className="mt-5 flex w-full items-center justify-between gap-4 rounded-3xl bg-danger-50 px-6 py-5 text-left transition-transform hover:-translate-y-0.5"
        >
          <div>
            <p className="text-[13px] font-bold text-danger-600">{t(language, 'checkFirst')}</p>
            <p className="mt-1 text-[16px] font-bold text-ink-900">
              {[clauseHeading(topRisk.original_text, language, topRisk.original_text_translated), riskTypeLabel(language, topRisk.risk_type)]
                .filter(Boolean)
                .join(' — ')}
            </p>
            <FormattedText
              text={topRisk.explanation}
              lead
              className="mt-1.5 text-[14px] text-ink-600"
            />
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
            const label = item === '전체' ? t(language, 'all') : riskLevelLabel(language, item)
            return (
              <button
                key={item}
                type="button"
                onClick={() => setFilter(item)}
                className={`rounded-full px-3.5 py-2 text-[14px] font-semibold transition-colors ${
                  active ? 'bg-ink-900 text-white' : 'bg-ink-50 text-ink-600 hover:bg-ink-100'
                }`}
              >
                {label} {count}
              </button>
            )
          })}
        </div>
        <div className="flex items-center gap-2">
          {/* 전체 낭독 (#82) — 조항별: 표제 → 판정 → 쉬운 설명 → 확인 질문 순 */}
          <button
            type="button"
            aria-pressed={reading}
            onClick={() => {
              if (reading) {
                stopSpeaking()
                setReading(false)
                return
              }
              const script = filtered
                .map((r) => {
                  const head = clauseHeading(r.original_text, language, r.original_text_translated)
                  const parts = [head, riskLevelLabel(language, r.risk_level), r.explanation,
                    ...r.check_questions]
                  return parts.filter(Boolean).join('. ')
                })
                .join('.\n')
              setReading(true)
              speak(script, language, () => setReading(false))
            }}
            className={`rounded-full px-3.5 py-2 text-[13px] font-bold transition-colors ${
              reading ? 'bg-ink-900 text-white' : 'bg-brand-50 text-brand-600 hover:bg-brand-100'
            }`}
          >
            🔊 {t(language, reading ? 'readAllStop' : 'readAll')}
          </button>
          {allQuestions && <CopyButton text={allQuestions}>{t(language, 'copyAllQuestions')}</CopyButton>}
        </div>
      </div>

      {/* 조항 카드 — 스트리밍 중엔 완료 순서대로 쌓인다 */}
      <div className="mt-4 space-y-3">
        {filtered.length === 0 ? (
          live ? (
            <>
              <div className="h-24 animate-pulse rounded-3xl bg-ink-25" />
              <div className="h-24 animate-pulse rounded-3xl bg-ink-25" />
            </>
          ) : (
            <Card className="px-6 py-10 text-center text-[14px] text-ink-400">
              {t(language, 'noClauses')}
            </Card>
          )
        ) : (
          filtered.map((result) => {
            // 카드 제목은 조항 표제(제N조…) — 유형은 괄호 보조 표기.
            // 표제가 없으면 기존처럼 유형만 표시한다.
            const heading = clauseHeading(result.original_text, language, result.original_text_translated)
            const typeLabel =
              result.risk_type === '해당 없음'
                ? t(language, 'standardClause')
                : riskTypeLabel(language, result.risk_type)
            return (
            <Card
              key={`${result.clause_id}#r${result.revision ?? 0}`}
              interactive
              onClick={() => onSelectClause(result.clause_id)}
              className="animate-fade-up p-6"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[15px] font-bold text-ink-900">
                    {heading ?? typeLabel}
                    {heading && (
                      <span className="ml-1.5 font-semibold text-ink-400">({typeLabel})</span>
                    )}
                  </p>
                  <p className="mt-1.5 line-clamp-2 text-[14px] leading-relaxed text-ink-400">
                    {result.explanation}
                  </p>
                </div>
                <RiskBadge
                  level={result.risk_level}
                  label={riskLevelLabel(language, result.risk_level)}
                />
              </div>
              {result.risk_level !== '안전' && (
                <div className="mt-3.5 rounded-xl bg-ink-25 px-4 py-3 text-[13px] text-ink-600">
                  <p className={`font-bold ${RISK_META[result.risk_level].badge.split(' ')[1]}`}>
                    {t(language, 'evidence')}
                  </p>
                  {result.analysis_failed ? (
                    <p className="mt-1 leading-relaxed">{t(language, 'analysisFailedNote')}</p>
                  ) : (
                    <FormattedText
                      text={result.risk_evidence_translated || result.risk_evidence}
                      className="mt-1"
                    />
                  )}
                </div>
              )}
              <p className="mt-3.5 text-[14px] font-bold text-brand-600">
                {t(language, 'seeDetail')} →
              </p>
            </Card>
            )
          })
        )}
      </div>

      {/* 깡통전세 위험 계산기 (#63) — 임대차 도메인일 때만. 조항 분석과 별개로
          계약서 밖 구조적 위험(전세가율)을 사용자 입력만으로 확인한다 */}
      {['주택임대차', '상가임대차', '임대차(구분불명)'].includes(domain) && (
        <div className="mt-6 space-y-3">
          <JeonseCalculator language={language} />
          <JeonseTimeline language={language} />
        </div>
      )}

      <div className="mt-9 flex flex-wrap justify-center gap-2.5">
        {/* 옵트인 로컬 기록 (#102 v1) — 서버 전송 없음, 이 기기에만 */}
        {!live && onSaveRecord && (
          recordSaved ? (
            <span className="inline-flex items-center rounded-2xl bg-safe-50 px-5 py-3 text-[14px] font-bold text-safe-700" role="status">
              ✅ {t(language, 'rcSaved')}
            </span>
          ) : (
            <Button variant="secondary" onClick={onSaveRecord}>
              🗂 {t(language, 'rcSave')}
            </Button>
          )
        )}
        <Button variant="secondary" onClick={onDone} disabled={live}>
          {t(language, 'finish')}
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
