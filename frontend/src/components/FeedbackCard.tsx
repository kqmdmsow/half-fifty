import { useState } from 'react'
import { Card } from './ui'
import { t, type LangCode } from '../i18n'

/** 사람 평가 수집 카드 (자문 §6 — "이해도 문항의 정답률, 읽는 데 걸린 시간과
 * 사용자 만족도를 비교하면 AI Judge의 clarity 점수보다 훨씬 설득력 있는 결과").
 *
 * 세 지표의 수집 장치:
 * - 정답률: 3문답 퀴즈(#92, jmjm_quiz_stats)
 * - 읽는 시간: 결과 표시 시점(resultsShownAt) → 만족도 응답 시점의 경과
 * - 만족도: 이 카드의 3단계 응답
 *
 * 무저장 원칙 유지: localStorage 익명 집계만(계약 내용 무관 숫자) — 서버
 * 수집은 팀 결정 후. 사람 평가 세션에서는 진행자가 참가자 기기에서
 * jmjm_feedback_stats를 읽어 기록한다 (#66 사람 평가 트랙).
 */
export function FeedbackCard({
  resultsShownAt,
  language = 'ko',
}: {
  resultsShownAt: number | null
  language?: LangCode
}) {
  const [answered, setAnswered] = useState(false)

  const submit = (rating: 1 | 2 | 3) => {
    setAnswered(true)
    try {
      const readingSeconds = resultsShownAt
        ? Math.round((Date.now() - resultsShownAt) / 1000)
        : null
      const prev = JSON.parse(
        localStorage.getItem('jmjm_feedback_stats')
          ?? '{"count":0,"ratingSum":0,"readingSecondsSum":0,"readingCount":0}',
      )
      localStorage.setItem('jmjm_feedback_stats', JSON.stringify({
        count: prev.count + 1,
        ratingSum: prev.ratingSum + rating,
        readingSecondsSum: prev.readingSecondsSum + (readingSeconds ?? 0),
        readingCount: prev.readingCount + (readingSeconds != null ? 1 : 0),
      }))
    } catch { /* 집계 실패는 무시 */ }
  }

  const options = [
    { rating: 1 as const, emoji: '😞', labelKey: 'fbBad' as const },
    { rating: 2 as const, emoji: '🙂', labelKey: 'fbOkay' as const },
    { rating: 3 as const, emoji: '😀', labelKey: 'fbGood' as const },
  ]

  return (
    <Card className="px-5 py-5">
      {answered ? (
        <p className="text-[15px] font-bold text-safe-700" role="status">
          <span aria-hidden>✅</span> {t(language, 'fbThanks')}
        </p>
      ) : (
        <>
          <p className="text-[15px] font-bold text-ink-900">{t(language, 'fbTitle')}</p>
          <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label={t(language, 'fbTitle')}>
            {options.map((option) => (
              <button
                key={option.rating}
                type="button"
                onClick={() => submit(option.rating)}
                className="flex items-center gap-2 rounded-2xl border border-ink-100 bg-white px-4 py-2.5 text-[14px] font-semibold text-ink-700 transition-colors hover:border-brand-500 hover:bg-brand-50"
              >
                <span aria-hidden className="text-[18px]">{option.emoji}</span>
                {t(language, option.labelKey)}
              </button>
            ))}
          </div>
          <p className="mt-2.5 text-[12px] leading-relaxed text-ink-300">{t(language, 'fbNote')}</p>
        </>
      )}
    </Card>
  )
}
