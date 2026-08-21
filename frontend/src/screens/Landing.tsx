import { Button, RiskBadge } from '../components/ui'
import { riskLevelLabel, t, type LangCode } from '../i18n'

export function LandingScreen({
  onStart,
  onApiInfo,
  language = 'ko',
}: {
  onStart: () => void
  onApiInfo?: () => void // 제휴·API 안내 (#85) — 미전달 시 링크 숨김
  language?: LangCode
}) {
  return (
    <div className="animate-fade-up">
      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-14 px-6 pb-24 pt-16 md:pt-24 lg:grid-cols-2">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3.5 py-1.5 text-[13px] font-bold text-brand-600">
            {t(language, 'heroBadge')}
          </span>
          <h1 className="mt-6 text-[38px] font-bold leading-[1.25] tracking-[-0.02em] text-ink-900 md:text-[52px]">
            {t(language, 'landingTitle1')}
            <br />
            {t(language, 'landingTitle2')}
          </h1>
          <p className="mt-5 max-w-md text-[17px] leading-relaxed text-ink-600">
            {t(language, 'landingSubtitle')}
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Button size="lg" onClick={onStart}>
              {t(language, 'landingCta')}
            </Button>
            <span className="text-[13px] font-medium text-ink-400">
              {t(language, 'heroNote')}
            </span>
          </div>
        </div>

        {/* 미리보기 목업 — 순수 장식이라 스크린리더에서 통째로 제외 (#82 2차):
            가짜 파일명·위험 배지가 실제 결과처럼 낭독되면 혼란만 준다 */}
        <div className="relative mx-auto w-full max-w-md" aria-hidden="true">
          <div className="rounded-3xl border border-ink-100 bg-white p-7 shadow-card">
            <p className="text-[13px] font-bold text-ink-400">전세계약서.pdf</p>
            <div className="mt-4 space-y-2.5">
              <div className="h-2.5 w-3/5 rounded-full bg-ink-50" />
              <div className="h-2.5 w-full rounded-full bg-ink-50" />
              <div className="h-2.5 w-4/5 rounded-full bg-ink-50" />
              <div className="h-2.5 w-11/12 rounded-full bg-ink-50" />
            </div>
            <div className="mt-6 rounded-2xl bg-danger-50 p-4">
              <RiskBadge level="위험" label={riskLevelLabel(language, '위험')} />
              <p className="mt-2.5 text-[14px] font-semibold leading-relaxed text-ink-900">
                "계약 종료 후 3개월 이내에 보증금을 반환할 수 있다."
              </p>
            </div>
          </div>
          <div className="absolute -bottom-8 -right-3 w-72 rounded-2xl border border-ink-100 bg-white p-5 shadow-float md:-right-8">
            <p className="text-[13px] font-bold text-danger-500">{t(language, 'mockTag')}</p>
            <p className="mt-1.5 text-[16px] font-bold text-ink-900">
              {t(language, 'mockTitle')}
            </p>
            <p className="mt-1.5 text-[13px] leading-relaxed text-ink-400">
              {t(language, 'mockBody')}
            </p>
          </div>
        </div>
      </section>

      {/* 기능 소개 */}
      <section className="border-t border-ink-50 bg-ink-25 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-center text-[26px] font-bold tracking-[-0.02em] text-ink-900 md:text-[32px]">
            {t(language, 'featuresTitle1')}
            <br />
            {t(language, 'featuresTitle2')}
          </h2>
          <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            <Feature
              emoji="📑"
              title={t(language, 'feat1Title')}
              body={t(language, 'feat1Body')}
            />
            <Feature
              emoji="💬"
              title={t(language, 'feat2Title')}
              body={t(language, 'feat2Body')}
            />
            <Feature
              emoji="🔍"
              title={t(language, 'feat3Title')}
              body={t(language, 'feat3Body')}
            />
            <Feature
              emoji="✅"
              title={t(language, 'feat4Title')}
              body={t(language, 'feat4Body')}
            />
          </div>
        </div>
      </section>

      {/* 이용 방법 */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-center text-[26px] font-bold tracking-[-0.02em] text-ink-900 md:text-[32px]">
            {t(language, 'stepsTitle')}
          </h2>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            <Step no="1" title={t(language, 'step1Title')} body={t(language, 'step1Body')} />
            <Step no="2" title={t(language, 'step2Title')} body={t(language, 'step2Body')} />
            <Step no="3" title={t(language, 'step3Title')} body={t(language, 'step3Body')} />
          </div>
        </div>
      </section>

      {/* 신뢰 */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <div className="rounded-3xl bg-ink-900 px-8 py-12 text-center md:px-16">
          <h2 className="text-[24px] font-bold text-white md:text-[28px]">
            {t(language, 'trustTitle')}
          </h2>
          <p className="mx-auto mt-3.5 max-w-lg text-[15px] leading-relaxed text-ink-300">
            {t(language, 'trustBody')}
          </p>
          <Button size="lg" className="mt-8 !bg-white !text-ink-900 hover:!bg-ink-50" onClick={onStart}>
            {t(language, 'trustCta')}
          </Button>
        </div>
      </section>

      {/* 푸터 */}
      <footer className="border-t border-ink-50 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-[13px] text-ink-400 md:flex-row">
          <span className="flex items-center gap-4">
            <span className="font-semibold">© 조목조목</span>
            {onApiInfo && (
              <button
                type="button"
                onClick={onApiInfo}
                className="font-semibold text-ink-600 underline underline-offset-2 hover:text-ink-900"
              >
                {t(language, 'apiFooterLink')}
              </button>
            )}
          </span>
          <span className="max-w-md text-center leading-relaxed md:text-right">
            {t(language, 'footerDisclaimer')}
          </span>
        </div>
      </footer>
    </div>
  )
}

function Feature({ emoji, title, body }: { emoji: string; title: string; body: string }) {
  return (
    <div className="rounded-3xl bg-white p-7 shadow-card">
      <span className="text-[28px]">{emoji}</span>
      <p className="mt-4 text-[17px] font-bold text-ink-900">{title}</p>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-400">{body}</p>
    </div>
  )
}

function Step({ no, title, body }: { no: string; title: string; body: string }) {
  return (
    <div className="rounded-3xl border border-ink-100 p-7">
      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 text-[15px] font-extrabold text-brand-600">
        {no}
      </span>
      <p className="mt-4 text-[17px] font-bold text-ink-900">{title}</p>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-400">{body}</p>
    </div>
  )
}
