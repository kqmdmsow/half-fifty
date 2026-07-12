import { useEffect, useRef, useState } from 'react'
import { Button } from '../components/ui'

const PHASES = [
  '계약서 텍스트 읽기',
  '조항 단위로 나누기',
  '불리할 수 있는 조항 찾기',
  '분석 결과 품질 확인하기',
]

export function ProgressScreen({
  loading,
  error,
  onCancel,
  onShowResult,
}: {
  loading: boolean
  error: string | null
  onCancel: () => void
  onShowResult: () => void
}) {
  const [percent, setPercent] = useState(4)
  const doneRef = useRef(false)

  // 진행률: 로딩 중엔 92%까지 천천히, 완료되면 100%
  useEffect(() => {
    if (!loading) {
      setPercent(100)
      return
    }
    const timer = setInterval(() => {
      setPercent((value) => Math.min(value + Math.random() * 7, 92))
    }, 450)
    return () => clearInterval(timer)
  }, [loading])

  // 완료되면 잠시 뒤 자동으로 결과 화면으로
  useEffect(() => {
    if (loading || error || doneRef.current) return
    doneRef.current = true
    const timer = setTimeout(onShowResult, 900)
    return () => clearTimeout(timer)
  }, [loading, error, onShowResult])

  const phaseIndex = loading ? Math.min(Math.floor(percent / 25), 3) : 4

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
        <span className="absolute text-[22px]">{error ? '⚠️' : loading ? '📄' : '✅'}</span>
      </div>

      <h1 className="mt-8 text-[24px] font-bold tracking-[-0.02em] text-ink-900 md:text-[28px]">
        {error
          ? '분석 서버에 연결하지 못했어요'
          : loading
            ? '계약서를 꼼꼼히 살펴보고 있어요'
            : '분석이 끝났어요'}
      </h1>
      <p className="mt-2.5 text-[15px] leading-relaxed text-ink-400">
        {error
          ? '예시 결과로 화면을 미리 확인할 수 있어요.'
          : loading
            ? '조항 단위로 나누고 위험 신호와 질문 목록을 정리해요.'
            : '잠시 후 결과 화면으로 이동해요.'}
      </p>

      {/* 진행 바 */}
      <div className="mt-8 h-1.5 w-full overflow-hidden rounded-full bg-ink-50">
        <div
          className={`h-full rounded-full transition-all duration-500 ${error ? 'bg-caution-500' : 'bg-brand-500'}`}
          style={{ width: `${error ? 100 : percent}%` }}
        />
      </div>

      {/* 단계 목록 */}
      <ul className="mt-7 w-full space-y-1 text-left">
        {PHASES.map((phase, index) => {
          const done = index < phaseIndex
          const active = index === phaseIndex
          return (
            <li
              key={phase}
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
                {phase}
              </span>
              <span className={done ? 'text-safe-500' : active ? 'text-brand-500' : 'text-ink-200'}>
                {done ? '✓' : active ? '진행 중' : ''}
              </span>
            </li>
          )
        })}
      </ul>

      <div className="mt-9 flex w-full gap-2.5">
        {error ? (
          <>
            <Button variant="secondary" size="lg" full onClick={onCancel}>
              다시 시도
            </Button>
            <Button size="lg" full onClick={onShowResult}>
              예시 결과 보기
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
