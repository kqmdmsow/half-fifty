import { useState } from 'react'
import { Card } from './ui'
import { fetchQuiz, type ClauseResult, type Language, type Persona, type QuizQuestion } from '../api'
import { t, type LangCode } from '../i18n'

/** 3문답 이해 확인 (#92 시그니처 ②) — "읽었다"가 아니라 "이해했다"를 확인.
 *
 * - 지연 생성: 사용자가 시작을 눌러야 worker 1콜 (분석 흐름과 무관)
 * - 문항은 agent 코드 가드(근거 조각 실존 검증) 통과분만 도착 — 빈 배열이면
 *   미노출 문구 (없는 게 틀린 것보다 낫다)
 * - 오답 시 해당 조항으로 이동 유도 (#76 재설명과 연결 예정)
 * - 정답률은 로컬 익명 집계만(localStorage) — 무저장 원칙 유지, 서버 수집은
 *   팀 결정 후 (#92)
 */
export function QuizCard({
  results,
  persona,
  language = 'ko',
  onSelectClause,
}: {
  results: ClauseResult[]
  persona: Persona
  language?: LangCode
  onSelectClause: (clauseId: string) => void
}) {
  const [phase, setPhase] = useState<'idle' | 'loading' | 'ready' | 'unavailable'>('idle')
  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [picks, setPicks] = useState<Record<number, number>>({})

  const start = async () => {
    setPhase('loading')
    setPicks({})
    try {
      // 위험도 높은 순으로 출제 재료 발췌 (상위 3개)
      const order = { 위험: 0, 주의: 1, 안전: 2 } as const
      const items = [...results]
        .sort((a, b) => order[a.risk_level] - order[b.risk_level])
        .slice(0, 3)
        .map(({ clause_id, explanation, risk_level, risk_type, risk_evidence }) => ({
          clause_id, explanation, risk_level, risk_type, risk_evidence,
        }))
      const qs = await fetchQuiz(items, persona, language as Language)
      if (qs.length === 0) {
        setPhase('unavailable')
        return
      }
      setQuestions(qs)
      setPhase('ready')
    } catch {
      setPhase('unavailable')
    }
  }

  const pick = (qi: number, ci: number) => {
    if (picks[qi] !== undefined) return // 문항당 1회만 (이해도 측정 왜곡 방지)
    const next = { ...picks, [qi]: ci }
    setPicks(next)
    // 로컬 익명 집계 (#92 로그 v1) — 개인정보·계약 내용 없이 건수만
    if (Object.keys(next).length === questions.length) {
      try {
        const correct = questions.filter((q, i) => next[i] === q.answer_index).length
        const prev = JSON.parse(localStorage.getItem('jmjm_quiz_stats') ?? '{"quizzes":0,"questions":0,"correct":0}')
        localStorage.setItem('jmjm_quiz_stats', JSON.stringify({
          quizzes: prev.quizzes + 1,
          questions: prev.questions + questions.length,
          correct: prev.correct + correct,
        }))
      } catch { /* 집계 실패는 무시 */ }
    }
  }

  const answered = Object.keys(picks).length
  const correctCount = questions.filter((q, i) => picks[i] === q.answer_index).length

  return (
    <Card className="px-5 py-5">
      <p className="text-[15px] font-bold text-ink-900">
        <span aria-hidden>✏️</span> {t(language, 'qzTitle')}
      </p>
      <p className="mt-1 text-[13px] leading-relaxed text-ink-400">{t(language, 'qzDesc')}</p>

      {phase === 'idle' && (
        <button
          type="button"
          onClick={start}
          className="mt-3 rounded-xl bg-brand-500 px-4 py-2.5 text-[14px] font-bold text-white transition-colors hover:bg-brand-600"
        >
          {t(language, 'qzStart')}
        </button>
      )}
      {phase === 'loading' && (
        <p className="mt-3 flex items-center gap-2 text-[13px] font-semibold text-ink-400" role="status">
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-brand-200 border-t-brand-500" aria-hidden />
          {t(language, 'qzLoading')}
        </p>
      )}
      {phase === 'unavailable' && (
        <p className="mt-3 rounded-xl bg-ink-25 px-4 py-3 text-[13px] font-semibold text-ink-400">
          {t(language, 'qzUnavailable')}
        </p>
      )}

      {phase === 'ready' && (
        <div className="mt-4 space-y-4">
          {questions.map((q, qi) => {
            const picked = picks[qi]
            const revealed = picked !== undefined
            const isCorrect = picked === q.answer_index
            return (
              <div key={qi} className="rounded-2xl bg-ink-25 p-4">
                <p className="text-[14px] font-bold text-ink-900">
                  Q{qi + 1}. {q.question}
                </p>
                <div className="mt-2.5 space-y-1.5" role="group" aria-label={`Q${qi + 1}`}>
                  {q.choices.map((choice, ci) => {
                    const isAnswer = ci === q.answer_index
                    const isPicked = picked === ci
                    return (
                      <button
                        key={ci}
                        type="button"
                        disabled={revealed}
                        onClick={() => pick(qi, ci)}
                        aria-pressed={isPicked}
                        className={`block w-full rounded-xl border px-3.5 py-2.5 text-left text-[14px] font-semibold transition-colors ${
                          revealed
                            ? isAnswer
                              ? 'border-safe-500 bg-safe-50 text-safe-700'
                              : isPicked
                                ? 'border-danger-500 bg-danger-50 text-danger-600'
                                : 'border-ink-100 bg-white text-ink-400'
                            : 'border-ink-100 bg-white text-ink-700 hover:border-brand-500 hover:bg-brand-50'
                        }`}
                      >
                        {choice}
                      </button>
                    )
                  })}
                </div>
                {revealed && (
                  <div className="mt-2.5 text-[13px] font-bold" role="status">
                    {isCorrect ? (
                      <span className="text-safe-700">✅ {t(language, 'qzCorrect')}</span>
                    ) : (
                      <span className="text-danger-600">
                        {t(language, 'qzWrong')}{' '}
                        <button
                          type="button"
                          onClick={() => onSelectClause(q.clause_id)}
                          className="underline underline-offset-2"
                        >
                          {t(language, 'qzGoClause')} →
                        </button>
                      </span>
                    )}
                  </div>
                )}
              </div>
            )
          })}

          {answered === questions.length && (
            <div className="flex items-center justify-between rounded-2xl bg-brand-50 px-4 py-3">
              <p className="text-[14px] font-bold text-brand-600" role="status">
                {t(language, 'qzScore', { n: correctCount, total: questions.length })}
              </p>
              <button
                type="button"
                onClick={start}
                className="text-[13px] font-bold text-ink-400 underline underline-offset-2"
              >
                {t(language, 'qzRetry')}
              </button>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
