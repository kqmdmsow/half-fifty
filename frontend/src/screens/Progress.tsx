import { useEffect, useRef, useState } from 'react'
import type { ClauseResult } from '../api'
import { Button, RiskBadge } from '../components/ui'
import { LensMark } from '../components/Brand'
import { t, type LangCode } from '../i18n'

const PHASE_KEYS = ['prPhase1', 'prPhase2', 'prPhase3', 'prPhase4'] as const

export function ProgressScreen({
  language = 'ko',
  loading,
  error,
  streamProgress,
  streamedClauses,
  onCancel,
  onRetry,
  onShowResult,
}: {
  language?: LangCode
  loading: boolean
  error: string | null
  streamProgress?: { done: number; total: number } | null
  streamedClauses?: ClauseResult[]
  onCancel: () => void
  onRetry?: () => void
  onShowResult: () => void
}) {
  const [percent, setPercent] = useState(4)
  const doneRef = useRef(false)
  const streaming = Boolean(streamProgress)

  // 진행률: 스트리밍이면 실제 완료 조항 수 기반, 아니면(파일 경로) 추정 애니메이션
  useEffect(() => {
    if (!loading) {
      setPercent(100)
      return
    }
    if (streamProgress) {
      // 조항 분석 90% + judge 검증 10%로 배분
      setPercent(streamProgress.total ? (streamProgress.done / streamProgress.total) * 90 : 5)
      return
    }
    const timer = setInterval(() => {
      setPercent((value) => Math.min(value + Math.random() * 7, 92))
    }, 450)
    return () => clearInterval(timer)
  }, [loading, streamProgress])

  // 완료되면 잠시 뒤 자동으로 결과 화면으로
  useEffect(() => {
    if (loading || error || doneRef.current) return
    doneRef.current = true
    const timer = setTimeout(onShowResult, 900)
    return () => clearTimeout(timer)
  }, [loading, error, onShowResult])

  const phaseIndex = loading
    ? streaming && streamProgress
      ? streamProgress.done >= streamProgress.total && streamProgress.total > 0
        ? 3 // 조항 분석 끝, judge 검증 중
        : 2
      : Math.min(Math.floor(percent / 25), 3)
    : 4

  const recentClauses = (streamedClauses ?? []).slice(-4).reverse()

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col items-center justify-center px-6 py-16 text-center">
      {/* 스피너 */}
      <div className="relative flex h-20 w-20 items-center justify-center">
        <svg className={loading ? 'animate-spin' : ''} viewBox="0 0 48 48" width="80" height="80">
          <circle cx="24" cy="24" r="20" fill="none" stroke="#F2F4F6" strokeWidth="5" />
          <circle
            cx="24"
            cy="24"
            r="20"
            fill="none"
            stroke={error ? '#FE9800' : loading ? '#3182F6' : '#00C471'}
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={loading ? '40 86' : '126 0'}
            className="transition-all duration-500"
          />
        </svg>
        {/* 분석 중에는 돋보기 마크가 조항을 들여다본다 (#134 브랜드 마크) */}
        <span className="absolute flex items-center justify-center">
          {loading && !error ? (
            <LensMark size={30} className="animate-lens-scan" />
          ) : (
            <span
              aria-hidden
              className={`text-[24px] font-extrabold ${error ? 'text-caution-500' : 'text-safe-500'}`}
            >
              {error ? '!' : '✓'}
            </span>
          )}
        </span>
      </div>

      <h1 className="mt-8 text-[24px] font-bold tracking-[-0.02em] text-ink-900 md:text-[28px]">
        {error
          ? t(language, 'prErrTitle')
          : loading
            ? t(language, 'progressTitle')
            : t(language, 'prDoneTitle')}
      </h1>
      <p className="mt-2.5 text-[15px] leading-relaxed text-ink-400">
        {error
          ? t(language, 'prErrDesc', { msg: error })
          : loading
            ? streaming && streamProgress?.total
              ? t(language, 'prStreamDesc', { done: streamProgress.done, total: streamProgress.total })
              : t(language, 'prLoadingDesc')
            : t(language, 'prDoneDesc')}
      </p>

      {/* 진행 바 */}
      <div className="mt-8 h-1.5 w-full overflow-hidden rounded-full bg-ink-50">
        <div
          className={`h-full rounded-full transition-all duration-500 ${error ? 'bg-caution-500' : 'bg-brand-500'}`}
          style={{ width: `${error ? 100 : percent}%` }}
        />
      </div>

      {/* 스트리밍: 방금 끝난 조항 실시간 표시 (Judge 검증 전 — 확정은 결과 화면에서) */}
      {streaming && recentClauses.length > 0 && (
        <ul className="mt-6 w-full space-y-1.5 text-left" aria-live="polite">
          {recentClauses.map((clause) => (
            <li
              key={clause.clause_id}
              className="flex items-center justify-between gap-3 rounded-xl bg-ink-25 px-3.5 py-2.5"
            >
              <span className="min-w-0 flex-1 truncate text-[13px] text-ink-700">
                {clause.original_text}
              </span>
              <RiskBadge level={clause.risk_level} />
            </li>
          ))}
        </ul>
      )}

      {/* 단계 목록 */}
      <ul className="mt-7 w-full space-y-1 text-left">
        {PHASE_KEYS.map((phaseKey, index) => {
          const done = index < phaseIndex
          const active = index === phaseIndex
          return (
            <li
              key={phaseKey}
              className="flex items-center justify-between rounded-xl px-3.5 py-2.5 text-[14px]"
            >
              <span
                className={
                  done
                    ? 'font-semibold text-ink-900'
                    : active
                      ? 'font-semibold text-brand-600'
                      : 'text-ink-300'
                }
              >
                {t(language, phaseKey)}
              </span>
              <span className={done ? 'text-safe-500' : active ? 'text-brand-500' : 'text-ink-200'}>
                {done ? '✓' : active ? t(language, 'prActive') : ''}
              </span>
            </li>
          )
        })}
      </ul>

      <div className="mt-9 flex w-full gap-2.5">
        {error ? (
          <>
            <Button variant="secondary" size="lg" full onClick={onCancel}>
              입력으로 돌아가기
            </Button>
            <Button size="lg" full onClick={onRetry ?? onCancel}>
              다시 시도
            </Button>
          </>
        ) : (
          loading && (
            <Button variant="ghost" full onClick={onCancel}>
              분석 취소
            </Button>
          )
        )}
      </div>
    </div>
  )
}
