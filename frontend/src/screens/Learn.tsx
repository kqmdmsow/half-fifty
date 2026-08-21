import { useEffect, useState } from 'react'
import { Button, Card, PageTitle } from '../components/ui'
import { t, type LangCode } from '../i18n'

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

  useEffect(() => {
    fetch(`${BASE_URL}/api/contracts/learn`)
      .then((r) => r.json())
      .then((d) => {
        setScams(d.scams ?? [])
        setRiskTypes(d.risk_types ?? [])
      })
      .catch(() => setScams([]))
  }, [])

  return (
    <div className="mx-auto max-w-3xl animate-fade-up px-6 py-12 md:py-16">
      <PageTitle title={t(language, 'lnPageTitle')} desc={t(language, 'lnPageDesc')} />
      {language !== 'ko' && (
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
                {rt.title}
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
                            — {c.result}
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

      <div className="mt-8 flex justify-center">
        <Button size="lg" onClick={onStart}>
          {t(language, 'landingCta')}
        </Button>
      </div>
    </div>
  )
}
