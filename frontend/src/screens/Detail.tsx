import { useEffect } from 'react'
import type { ClauseResult } from '../api'
import { Button, CopyButton, RiskBadge } from '../components/ui'
import { RISK_META } from '../data/sample'
import { riskLevelLabel, riskTypeLabel, t, type LangCode } from '../i18n'
import { clauseHeading } from '../clauseTitle'
import { FormattedText } from '../components/FormattedText'
import { speak, stopSpeaking } from '../tts'

export function DetailScreen({
  clauseId,
  results,
  voiceGuide,
  language = 'ko',
  onSelectClause,
  onBack,
  onDone,
}: {
  clauseId: string
  results: ClauseResult[]
  voiceGuide: boolean
  language?: LangCode
  onSelectClause: (clauseId: string) => void
  onBack: () => void
  onDone: () => void
}) {
  const clause = results.find((result) => result.clause_id === clauseId) ?? results[0]

  // 음성 안내: 화면 진입 시 설명 읽기 (기기 최적 한국어 보이스 자동 선택 — src/tts.ts)
  useEffect(() => {
    if (!voiceGuide || !clause) return
    speak(clause.explanation)
    return () => stopSpeaking()
  }, [voiceGuide, clause])

  // 결과가 아직 없으면 렌더링하지 않는다 (가짜 예시 폴백 제거 후의 방어선).
  // 훅 규칙 때문에 useEffect 뒤에 위치해야 한다.
  if (!clause) return null

  const questions = clause.check_questions.length
    ? clause.check_questions
    : ['이 조항은 그대로 유지해야 하나요?']

  return (
    <div className="mx-auto max-w-5xl animate-fade-up px-6 py-10 md:py-14">
      <button
        type="button"
        onClick={onBack}
        className="mb-6 inline-flex items-center gap-1.5 text-[14px] font-semibold text-ink-400 transition-colors hover:text-ink-900"
      >
        ← {t(language, 'backToSummary')}
      </button>

      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        {/* 조항 목록 */}
        <aside className="lg:border-r lg:border-ink-50 lg:pr-6">
          <p className="px-1 text-[13px] font-bold text-ink-400">{t(language, 'clauseList')}</p>
          <nav className="mt-3 flex gap-2 overflow-x-auto pb-2 lg:flex-col lg:overflow-visible lg:pb-0">
            {results.map((result) => {
              const active = result.clause_id === clause.clause_id
              return (
                <button
                  key={result.clause_id}
                  type="button"
                  onClick={() => onSelectClause(result.clause_id)}
                  className={`flex shrink-0 items-center gap-2.5 rounded-2xl px-4 py-3 text-left text-[14px] font-semibold transition-colors ${
                    active
                      ? 'bg-ink-900 text-white'
                      : 'bg-ink-25 text-ink-600 hover:bg-ink-50'
                  }`}
                >
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full ${RISK_META[result.risk_level].dot}`}
                  />
                  <span className="whitespace-nowrap lg:whitespace-normal">
                    {clauseHeading(result.original_text, language, result.original_text_translated) ??
                      (result.risk_type === '해당 없음'
                        ? t(language, 'standardClause')
                        : riskTypeLabel(language, result.risk_type))}
                  </span>
                </button>
              )
            })}
          </nav>
        </aside>

        {/* 상세 */}
        <article>
          <div className="flex items-start justify-between gap-4">
            <div>
              <RiskBadge level={clause.risk_level} label={riskLevelLabel(language, clause.risk_level)} />
              <h1 className="mt-3 text-[24px] font-bold leading-snug tracking-[-0.02em] text-ink-900 md:text-[28px]">
                {clauseHeading(clause.original_text, language, clause.original_text_translated) ??
                  (clause.risk_type === '해당 없음'
                    ? t(language, 'standardClauseLong')
                    : riskTypeLabel(language, clause.risk_type))}
              </h1>
              {clauseHeading(clause.original_text, language, clause.original_text_translated) && (
                <p className="mt-1.5 text-[14px] font-bold text-ink-400">
                  {clause.risk_type === '해당 없음'
                    ? t(language, 'standardClauseLong')
                    : riskTypeLabel(language, clause.risk_type)}
                </p>
              )}
            </div>
          </div>

          <Section title={t(language, 'explainSimply')}>
            <FormattedText text={clause.explanation} lead />
          </Section>

          {clause.risk_level !== '안전' && (
            <Section title={t(language, 'whyCheck')}>
              <FormattedText text={clause.risk_evidence} />
            </Section>
          )}

          <div className="mt-6 rounded-2xl border border-danger-500/20 bg-danger-50 p-5">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[14px] font-bold text-ink-900">{t(language, 'originalText')}</p>
              <CopyButton text={clause.original_text} className="!bg-white" />
            </div>
            <p className="mt-2.5 text-[15px] leading-loose text-ink-700">{clause.original_text}</p>
            {clause.original_text_translated && (
              <div className="mt-3 border-t border-danger-500/10 pt-3">
                <p className="text-[12px] font-bold text-ink-400">{t(language, 'translationLabel')}</p>
                <p className="mt-1 text-[14px] leading-relaxed text-ink-600">
                  {clause.original_text_translated}
                </p>
              </div>
            )}
          </div>

          <div className="mt-7">
            <p className="text-[16px] font-bold text-ink-900">{t(language, 'askOther')}</p>
            {language !== 'ko' && (
              <p className="mt-1 text-[13px] text-ink-400">{t(language, 'askKoreanHint')}</p>
            )}
            <div className="mt-3 space-y-2.5">
              {questions.map((question, index) => {
                const translated = clause.check_questions_translated?.[index]
                return (
                  <div
                    key={question}
                    className="flex items-center justify-between gap-3 rounded-2xl border border-ink-100 bg-white px-5 py-4"
                  >
                    <div className="min-w-0 flex-1">
                      {/* 번역이 있으면 이해용 번역을 먼저, 상대방에게 보여줄 한국어를 아래에 */}
                      {translated && (
                        <p className="text-[14px] font-semibold leading-relaxed text-ink-900">
                          {translated}
                        </p>
                      )}
                      <p
                        className={
                          translated
                            ? 'mt-1.5 rounded-lg bg-ink-25 px-2.5 py-1.5 text-[13px] leading-relaxed text-ink-600'
                            : 'text-[14px] leading-relaxed text-ink-700'
                        }
                      >
                        {translated && (
                          <span className="mr-1.5 font-bold text-ink-400">
                            {t(language, 'inKorean')}:
                          </span>
                        )}
                        {question}
                      </p>
                    </div>
                    <CopyButton text={question} />
                  </div>
                )
              })}
            </div>
          </div>

          <div className="mt-9 flex flex-col-reverse justify-between gap-2.5 md:flex-row">
            <Button variant="secondary" onClick={onBack}>
              {t(language, 'otherClauses')}
            </Button>
            <Button onClick={onDone}>{t(language, 'finishDetail')}</Button>
          </div>
        </article>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="text-[14px] font-bold text-ink-400">{title}</h2>
      <div className="mt-2 rounded-2xl bg-ink-25 p-5 text-[15px] leading-loose text-ink-700">
        {children}
      </div>
    </section>
  )
}
