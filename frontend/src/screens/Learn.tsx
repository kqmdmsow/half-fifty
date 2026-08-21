import { useEffect, useState } from 'react'
import { Button, Card, PageTitle } from '../components/ui'
import { t, type LangCode } from '../i18n'

/** 교육 페이지 (#104) + 내장 챗봇 (#103) — 분석 도구를 넘어선 상설 학습 탭.
 *
 * - 콘텐츠는 agent GET /learn 단일 원천(전세사기 5대 수법, 골든셋·실증 연구
 *   재활용) — 콘텐츠 본문은 한국어(단계적 현지화, UI 크롬만 16언어)
 * - 챗봇 컨텍스트는 서버 사본만 사용 — 클라이언트는 질문 텍스트만 보낸다
 *   (인젝션 방어 #67과 동일 원칙), 개별 법률 자문은 전문가 상담 안내로 제한
/** 교육 페이지 (#104) — 분석 도구를 넘어선 상설 학습 탭.
 *
 * 콘텐츠는 agent GET /learn 단일 원천(전세사기 5대 수법, 골든셋·실증 연구
 * 재활용) — 콘텐츠 본문은 한국어(단계적 현지화, UI 크롬만 16언어).
 *
 * 내장 챗봇(#103)은 별도 PR — 세션당 대화 횟수 상한 + 인젝션 방어(#131/#149
 * 재사용) 조건을 걸고 나서 합류 예정.
 */
const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8080'

interface Scam {
  id: string
  title: string
  what: string
  signal: string
  outside: string
  case: string
}

interface ChatTurn {
  role: 'user' | 'bot'
  text: string
}

export function LearnScreen({
  language = 'ko',
  onStart,
}: {
  language?: LangCode
  onStart: () => void
}) {
  const [scams, setScams] = useState<Scam[]>([])
  const [question, setQuestion] = useState('')
  const [chat, setChat] = useState<ChatTurn[]>([])
  const [asking, setAsking] = useState(false)

  useEffect(() => {
    fetch(`${BASE_URL}/api/contracts/learn`)
      .then((r) => r.json())
      .then((d) => setScams(d.scams ?? []))
      .catch(() => setScams([]))
  }, [])

  const ask = async () => {
    const q = question.trim()
    if (!q || asking) return
    setAsking(true)
    setQuestion('')
    setChat((prev) => [...prev, { role: 'user', text: q }])
    try {
      const res = await fetch(`${BASE_URL}/api/contracts/learn-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, language }),
      })
      const data = await res.json()
      setChat((prev) => [
        ...prev,
        { role: 'bot', text: data.ok ? data.answer : t(language, 'lnChatFail') },
      ])
    } catch {
      setChat((prev) => [...prev, { role: 'bot', text: t(language, 'lnChatFail') }])
    } finally {
      setAsking(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl animate-fade-up px-6 py-12 md:py-16">
      <PageTitle title={t(language, 'lnTitle')} desc={t(language, 'lnDesc')} />
      {language !== 'ko' && (
        <p className="mt-2 text-[13px] font-semibold text-ink-400">{t(language, 'lnKoNote')}</p>
      )}

      <div className="mt-8 space-y-4">
        {scams.map((scam, i) => (
          <Card key={scam.id} className="p-6">
            <h2 className="text-[17px] font-bold text-ink-900">
              <span aria-hidden className="mr-1.5 text-brand-500">{i + 1}.</span>
              {scam.title}
            </h2>
            <p className="mt-2 text-[14px] leading-relaxed text-ink-700">{scam.what}</p>
            <div className="mt-3.5 grid gap-2.5 md:grid-cols-2">
              <div className="rounded-2xl bg-danger-50 px-4 py-3">
                <p className="text-[12px] font-bold text-danger-600">{t(language, 'lnSignal')}</p>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-700">{scam.signal}</p>
              </div>
              <div className="rounded-2xl bg-brand-50 px-4 py-3">
                <p className="text-[12px] font-bold text-brand-600">{t(language, 'lnOutside')}</p>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-700">{scam.outside}</p>
              </div>
            </div>
            <p className="mt-3 text-[12px] leading-relaxed text-ink-400">
              <span className="font-bold">{t(language, 'lnCase')}:</span> {scam.case}
            </p>
          </Card>
        ))}
      </div>

      {/* 내장 챗봇 (#103) */}
      <Card className="mt-8 p-6">
        <h2 className="text-[16px] font-bold text-ink-900">
          <span aria-hidden>💬</span> {t(language, 'lnChatTitle')}
        </h2>
        <p className="mt-1 text-[12px] leading-relaxed text-ink-400">{t(language, 'lnChatScope')}</p>

        {chat.length > 0 && (
          <div className="mt-4 max-h-80 space-y-2.5 overflow-y-auto" aria-live="polite">
            {chat.map((turn, i) => (
              <div
                key={i}
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-[14px] leading-relaxed ${
                  turn.role === 'user'
                    ? 'ml-auto bg-brand-500 text-white'
                    : 'bg-ink-25 text-ink-700'
                }`}
              >
                {turn.text}
              </div>
            ))}
            {asking && (
              <div className="flex items-center gap-2 px-2 text-[13px] text-ink-400" role="status">
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-brand-200 border-t-brand-500" aria-hidden />
                …
              </div>
            )}
          </div>
        )}

        <div className="mt-4 flex gap-2">
          <input
            type="text"
            value={question}
            maxLength={500}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && ask()}
            placeholder={t(language, 'lnChatPlaceholder')}
            className="min-w-0 flex-1 rounded-xl border border-ink-100 bg-white px-3.5 py-2.5 text-[14px] text-ink-900 outline-none placeholder:text-ink-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-50"
          />
          <button
            type="button"
            onClick={ask}
            disabled={asking || !question.trim()}
            className="shrink-0 rounded-xl bg-brand-500 px-4 py-2.5 text-[14px] font-bold text-white transition-colors hover:bg-brand-600 disabled:opacity-40"
          >
            {t(language, 'lnChatSend')}
          </button>
        </div>
      </Card>

      <div className="mt-8 flex justify-center">
        <Button size="lg" onClick={onStart}>
          {t(language, 'landingCta')}
        </Button>
      </div>
    </div>
  )
}
