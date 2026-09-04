import { useEffect, useState } from 'react'
import { Button, Card, PageTitle } from '../components/ui'
import { riskTypeLabel, t, type LangCode } from '../i18n'

/** 교육 페이지 (#104) + 내장 챗봇 (#103) — 분석 도구를 넘어선 상설 학습 탭.
 *
 * - 콘텐츠는 agent GET /learn 단일 원천(전세사기 5대 수법·위험 유형 10종,
 *   골든셋·실증 연구 재활용) — 정적 번역본이 있는 언어는 번역해서 받는다.
 * - 챗봇 컨텍스트는 서버 사본만 사용 — 클라이언트는 질문 텍스트만 보낸다
 *   (인젝션 방어 #67과 동일 원칙). 비용 상한(IP당 시간당 20회, 백엔드)과
 *   인젝션 방어(#131 규칙 탐지기, 에이전트)를 통과한 질문만 LLM까지 간다.
 *   개별 법률 자문은 전문가 상담 안내로 제한.
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

interface RiskCase {
  case_id: string
  agency: string
  citation: string
  result: string
}

interface RiskTypeGuide {
  id: string
  title: string
  what: string
  signals: string[]
  tip: string
  cases: RiskCase[]
}

interface ChatTurn {
  role: 'user' | 'bot'
  text: string
}

// 연속 전송 방지용 클라이언트 쿨다운 — 서버측 시간당 상한의 보조 장치.
const ASK_COOLDOWN_MS = 3000

export function LearnScreen({
  language = 'ko',
  onStart,
}: {
  language?: LangCode
  onStart: () => void
}) {
  const [scams, setScams] = useState<Scam[]>([])
  const [riskTypes, setRiskTypes] = useState<RiskTypeGuide[]>([])
  const [openType, setOpenType] = useState<string | null>(null)

  // 콘텐츠는 언어별 정적 번역본 — 언어를 바꾸면 다시 받아온다.
  // content_language가 ko로 돌아오면(번역 미보유 언어) 한국어 안내문을 띄운다.
  const [contentLanguage, setContentLanguage] = useState('ko')
  useEffect(() => {
    fetch(`${BASE_URL}/api/contracts/learn?language=${language}`)
      .then((r) => r.json())
      .then((d) => {
        setScams(d.scams ?? [])
        setRiskTypes(d.risk_types ?? [])
        setContentLanguage(d.content_language ?? 'ko')
      })
      .catch(() => setScams([]))
  }, [language])

  // 내장 챗봇 (#103) — 서버가 비용 상한(429)·인젝션 방어(reason: 'blocked')를
  // 판정하고, 여기서는 결과 문구만 언어별로 매핑한다.
  const [question, setQuestion] = useState('')
  const [chat, setChat] = useState<ChatTurn[]>([])
  const [asking, setAsking] = useState(false)
  const [cooldown, setCooldown] = useState(false)

  const ask = async () => {
    const q = question.trim()
    if (!q || asking || cooldown) return
    setAsking(true)
    setQuestion('')
    setChat((prev) => [...prev, { role: 'user', text: q }])
    try {
      const res = await fetch(`${BASE_URL}/api/contracts/learn-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, language }),
      })
      let text: string
      if (res.status === 429) {
        text = t(language, 'lnChatLimited')
      } else {
        const data = await res.json()
        text = data.ok
          ? data.answer
          : data.reason === 'blocked'
            ? t(language, 'lnChatBlocked')
            : t(language, 'lnChatFail')
      }
      setChat((prev) => [...prev, { role: 'bot', text }])
    } catch {
      setChat((prev) => [...prev, { role: 'bot', text: t(language, 'lnChatFail') }])
    } finally {
      setAsking(false)
      setCooldown(true)
      setTimeout(() => setCooldown(false), ASK_COOLDOWN_MS)
    }
  }

  return (
    <div className="mx-auto max-w-3xl animate-fade-up px-6 py-12 md:py-16">
      <PageTitle title={t(language, 'lnPageTitle')} desc={t(language, 'lnPageDesc')} />
      {language !== 'ko' && contentLanguage === 'ko' && (
        <p className="mt-2 text-[13px] font-semibold text-ink-400">{t(language, 'lnKoNote')}</p>
      )}

      {/* 위험 유형 카테고리 (#104 확장) — 그리드에서 고르면 상세가 열린다 */}
      <h2 className="mt-10 text-[19px] font-bold text-ink-900">{t(language, 'lnTypesTitle')}</h2>
      <p className="mt-1.5 text-[13px] leading-relaxed text-ink-400">{t(language, 'lnTypesDesc')}</p>
      <div className="mt-5 grid gap-2.5 sm:grid-cols-2">
        {riskTypes.map((rt) => {
          const open = openType === rt.id
          return (
            <div key={rt.id} className={open ? 'sm:col-span-2' : ''}>
              <button
                type="button"
                aria-expanded={open}
                onClick={() => setOpenType(open ? null : rt.id)}
                className={`flex w-full items-center justify-between gap-3 rounded-2xl border px-5 py-4 text-left text-[15px] font-bold transition-colors ${
                  open
                    ? 'border-brand-500 bg-brand-50 text-brand-600'
                    : 'border-ink-100 bg-white text-ink-900 hover:border-brand-500/40 hover:bg-brand-50/50'
                }`}
              >
                {riskTypeLabel(language, rt.title)}
                <span aria-hidden className="text-[13px] text-ink-300">
                  {open ? '−' : '+'}
                </span>
              </button>
              {open && (
                <Card className="mt-2 p-6">
                  <p className="text-[14px] leading-relaxed text-ink-700">{rt.what}</p>
                  <div className="mt-3.5 rounded-2xl bg-danger-50 px-4 py-3">
                    <p className="text-[12px] font-bold text-danger-600">{t(language, 'lnSignal')}</p>
                    <ul className="mt-1.5 space-y-1">
                      {rt.signals.map((sig) => (
                        <li key={sig} className="flex items-start gap-2 text-[13px] leading-relaxed text-ink-700">
                          <span aria-hidden className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-danger-500" />
                          {sig}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="mt-2.5 rounded-2xl bg-brand-50 px-4 py-3">
                    <p className="text-[12px] font-bold text-brand-600">{t(language, 'lnTip')}</p>
                    <p className="mt-1 text-[13px] leading-relaxed text-ink-700">{rt.tip}</p>
                  </div>
                  {rt.cases.length > 0 ? (
                    <div className="mt-3">
                      <p className="text-[12px] font-bold text-ink-600">{t(language, 'lnCases')}</p>
                      <ul className="mt-1.5 space-y-1.5">
                        {rt.cases.map((c) => (
                          <li key={c.case_id} className="text-[12.5px] leading-relaxed text-ink-400">
                            <span className="font-semibold text-ink-600">
                              {c.agency} {c.citation}
                            </span>{' '}
                            ({c.result})
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <p className="mt-3 text-[12px] leading-relaxed text-ink-400">
                      {t(language, 'lnNoCases')}
                    </p>
                  )}
                </Card>
              )}
            </div>
          )
        })}
      </div>

      {/* 전세사기 5대 수법 — 임대차 특화 심화 섹션 */}
      <h2 className="mt-12 text-[19px] font-bold text-ink-900">{t(language, 'lnTitle')}</h2>
      <p className="mt-1.5 text-[13px] leading-relaxed text-ink-400">{t(language, 'lnDesc')}</p>

      <div className="mt-5 space-y-4">
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
          {t(language, 'lnChatTitle')}
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
            disabled={asking || cooldown || !question.trim()}
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
