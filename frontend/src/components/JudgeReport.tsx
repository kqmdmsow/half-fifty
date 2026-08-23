import { Card } from './ui'
import { t, type LangCode } from '../i18n'
import { VERIFICATION } from '../data/verification'

/** AI 검증 리포트 (#53) — judge 점수 4종·재시도 횟수·needs_review 노출.
 *
 * 프로젝트 핵심 차별점(채점 AI의 게이팅)이 지금까지는 내부에서만 돌았다 —
 * 이 카드는 그 과정을 사용자·심사위원에게 보여준다. 점수는 표시 전용이며
 * 재시도·검토 필요 판단은 agent 게이트(FAITHFULNESS_MIN·JUDGE_THRESHOLD)가
 * 이미 내린 결과를 그대로 전달한다.
 */
const ASPECTS = [
  { key: 'clarity', labelKey: 'jgClarity' },
  { key: 'faithfulness', labelKey: 'jgFaith' },
  { key: 'risk_coverage', labelKey: 'jgCoverage' },
  { key: 'actionability', labelKey: 'jgAction' },
] as const

export function JudgeReport({
  scores,
  retryCount,
  needsReview,
  language = 'ko',
}: {
  scores: Record<string, number>
  retryCount: number
  needsReview: boolean
  language?: LangCode
}) {
  const available = ASPECTS.filter((a) => typeof scores[a.key] === 'number')
  if (available.length === 0) return null

  return (
    <Card className="px-5 py-5">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-[15px] font-bold text-ink-900">
          <span aria-hidden>🛡️</span> {t(language, 'jgTitle')}
        </p>
        <span
          className={`rounded-lg px-2 py-0.5 text-[12px] font-bold ${
            needsReview ? 'bg-caution-50 text-caution-700' : 'bg-safe-50 text-safe-700'
          }`}
        >
          {needsReview ? t(language, 'jgNeedsReview').split(':')[0] : t(language, 'jgPass')}
        </span>
        <span className="text-[12px] font-semibold text-ink-400">
          {retryCount > 0 ? t(language, 'jgRetryN', { n: retryCount }) : t(language, 'jgRetryNone')}
        </span>
      </div>
      <p className="mt-1 text-[13px] leading-relaxed text-ink-400">{t(language, 'jgDesc')}</p>

      <div className="mt-3.5 grid gap-x-6 gap-y-2.5 md:grid-cols-2">
        {available.map((aspect) => {
          const score = scores[aspect.key]
          const pct = Math.max(0, Math.min(100, (score / 5) * 100))
          const tone = score >= 4 ? 'bg-safe-500' : score >= 3 ? 'bg-caution-500' : 'bg-danger-500'
          return (
            <div key={aspect.key}>
              <div className="flex items-baseline justify-between">
                <span className="text-[13px] font-semibold text-ink-600">
                  {t(language, aspect.labelKey)}
                </span>
                <span className="text-[13px] font-bold text-ink-900">
                  {score.toFixed(1)}
                  <span className="ml-1 font-medium text-ink-300">/ 5</span>
                </span>
              </div>
              <div
                className="mt-1 h-1.5 overflow-hidden rounded-full bg-ink-50"
                role="img"
                aria-label={`${t(language, aspect.labelKey)} ${score.toFixed(1)} ${t(language, 'jgScale')}`}
              >
                <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
              </div>
            </div>
          )
        })}
      </div>

      {needsReview && (
        <p className="mt-3.5 rounded-xl bg-caution-50 px-4 py-3 text-[13px] font-semibold leading-relaxed text-caution-700" role="alert">
          <span aria-hidden>⚠️</span> {t(language, 'jgNeedsReview')}
        </p>
      )}

      {/* 판정 기준 자체의 근거 (#169) — 위 점수가 "이번 분석의 품질"이라면
          이 줄은 "판정 기준을 무엇으로 검증했나"다. 둘은 다른 층위다. */}
      <p className="mt-3.5 border-t border-ink-50 pt-3 text-[12px] leading-relaxed text-ink-400">
        {t(language, 'trGolden', { n: VERIFICATION.goldenRows })} ·{' '}
        {t(language, 'trNormalFp', { n: VERIFICATION.normalClauses })}
      </p>
    </Card>
  )
}
