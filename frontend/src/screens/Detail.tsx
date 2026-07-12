import { useEffect } from 'react'
import type { ClauseResult } from '../api'
import { Button, CopyButton, RiskBadge } from '../components/ui'
import { RISK_META } from '../data/sample'

export function DetailScreen({
  clauseId,
  results,
  voiceGuide,
  onSelectClause,
  onBack,
  onDone,
}: {
  clauseId: string
  results: ClauseResult[]
  voiceGuide: boolean
  onSelectClause: (clauseId: string) => void
  onBack: () => void
  onDone: () => void
}) {
  const clause = results.find((result) => result.clause_id === clauseId) ?? results[0]

  // 음성 안내: 화면 진입 시 설명 읽기
  useEffect(() => {
    if (!voiceGuide || !('speechSynthesis' in window)) return
    const utterance = new SpeechSynthesisUtterance(clause.explanation)
    utterance.lang = 'ko-KR'
    utterance.rate = 0.95
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utterance)
    return () => window.speechSynthesis.cancel()
  }, [voiceGuide, clause])

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
        ← 결과 요약으로
      </button>

      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        {/* 조항 목록 */}
        <aside className="lg:border-r lg:border-ink-50 lg:pr-6">
          <p className="px-1 text-[13px] font-bold text-ink-400">조항 목록</p>
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
                    {result.risk_type === '해당 없음' ? '표준 조항' : result.risk_type}
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
              <RiskBadge level={clause.risk_level} />
              <h1 className="mt-3 text-[24px] font-bold leading-snug tracking-[-0.02em] text-ink-900 md:text-[28px]">
                {clause.risk_type === '해당 없음' ? '표준적인 조항이에요' : clause.risk_type}
              </h1>
            </div>
          </div>

          <Section title="쉽게 설명하면">
            <p>{clause.explanation}</p>
          </Section>

          {clause.risk_level !== '안전' && (
            <Section title="왜 확인해야 하나요?">
              <p>{clause.risk_evidence}</p>
            </Section>
          )}

          <div className="mt-6 rounded-2xl border border-danger-500/20 bg-danger-50 p-5">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[14px] font-bold text-ink-900">계약서 원문</p>
              <CopyButton text={clause.original_text} className="!bg-white" />
            </div>
            <p className="mt-2.5 text-[15px] leading-loose text-ink-700">{clause.original_text}</p>
          </div>

          <div className="mt-7">
            <p className="text-[16px] font-bold text-ink-900">계약 상대방에게 물어보세요</p>
            <div className="mt-3 space-y-2.5">
              {questions.map((question) => (
                <div
                  key={question}
                  className="flex items-center justify-between gap-3 rounded-2xl border border-ink-100 bg-white px-5 py-4"
                >
                  <span className="text-[14px] leading-relaxed text-ink-700">{question}</span>
                  <CopyButton text={question} />
                </div>
              ))}
            </div>
          </div>

          <div className="mt-9 flex flex-col-reverse justify-between gap-2.5 md:flex-row">
            <Button variant="secondary" onClick={onBack}>
              다른 조항 보기
            </Button>
            <Button onClick={onDone}>확인 끝내고 결과 활용하기</Button>
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
