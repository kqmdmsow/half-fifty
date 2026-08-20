import { Button, RiskBadge } from '../components/ui'
import { Reveal } from '../components/Reveal'
import { LANGUAGES, riskLevelLabel, t, type LangCode } from '../i18n'

export function LandingScreen({
  onStart,
  language = 'ko',
}: {
  onStart: () => void
  language?: LangCode
}) {
  return (
    <div className="animate-fade-up">
      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-14 px-6 pb-24 pt-16 md:pt-24 lg:grid-cols-2">
        <div className="hero-stagger">
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

        {/* 미리보기 목업 */}
        <div className="relative mx-auto w-full max-w-md">
          {/* 문서 카드: 둥실 + 스켈레톤 라인은 분석 중처럼 시머 (#134 모션) */}
          <div className="animate-float rounded-3xl border border-ink-100 bg-white p-7 shadow-card">
            <p className="text-[13px] font-bold text-ink-400">전세계약서.pdf</p>
            <div className="mt-4 space-y-2.5">
              {['w-3/5', 'w-full', 'w-4/5', 'w-11/12'].map((w) => (
                <div
                  key={w}
                  className={`h-2.5 ${w} animate-shimmer rounded-full bg-gradient-to-r from-ink-50 via-ink-100 to-ink-50 bg-[length:200%_100%]`}
                />
              ))}
            </div>
            <div className="mt-6 rounded-2xl bg-danger-50 p-4">
              <RiskBadge level="위험" label={riskLevelLabel(language, '위험')} />
              <p className="mt-2.5 text-[14px] font-semibold leading-relaxed text-ink-900">
                "계약 종료 후 3개월 이내에 보증금을 반환할 수 있다."
              </p>
            </div>
          </div>
          <div className="absolute -bottom-8 -right-3 w-72 animate-float-delay rounded-2xl border border-ink-100 bg-white p-5 shadow-float md:-right-8">
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

      {/* 지원 언어 마퀴 (#134 모션) — 장식이므로 스크린리더에서 제외,
          reduced-motion에서는 애니메이션이 정지돼 첫 화면 분량만 보인다 */}
      <div aria-hidden className="overflow-hidden border-t border-ink-50 py-5 [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
        <div className="flex w-max animate-marquee gap-3">
          {[...LANGUAGES, ...LANGUAGES].map((item, i) => (
            <span
              key={`${item.id}-${i}`}
              className="whitespace-nowrap rounded-full bg-ink-50 px-4 py-2 text-[13px] font-bold text-ink-600"
            >
              {item.label}
            </span>
          ))}
        </div>
      </div>

      {/* 기능 소개 */}
      <section className="border-t border-ink-50 bg-ink-25 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <Reveal>
            <h2 className="text-center text-[26px] font-bold tracking-[-0.02em] text-ink-900 md:text-[32px]">
              {t(language, 'featuresTitle1')}
              <br />
              {t(language, 'featuresTitle2')}
            </h2>
          </Reveal>
          <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            {(
              [
                ['📑', 'feat1Title', 'feat1Body'],
                ['💬', 'feat2Title', 'feat2Body'],
                ['🔍', 'feat3Title', 'feat3Body'],
                ['✅', 'feat4Title', 'feat4Body'],
              ] as const
            ).map(([emoji, titleKey, bodyKey], i) => (
              <Reveal key={titleKey} delay={i * 90}>
                <Feature emoji={emoji} title={t(language, titleKey)} body={t(language, bodyKey)} />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* 이용 방법 */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <Reveal>
            <h2 className="text-center text-[26px] font-bold tracking-[-0.02em] text-ink-900 md:text-[32px]">
              {t(language, 'stepsTitle')}
            </h2>
          </Reveal>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {(
              [
                ['1', 'step1Title', 'step1Body'],
                ['2', 'step2Title', 'step2Body'],
                ['3', 'step3Title', 'step3Body'],
              ] as const
            ).map(([no, titleKey, bodyKey], i) => (
              <Reveal key={titleKey} delay={i * 110}>
                <Step no={no} title={t(language, titleKey)} body={t(language, bodyKey)} />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* 신뢰 */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <Reveal>
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
        </Reveal>
      </section>

      {/* 푸터 */}
      <footer className="border-t border-ink-50 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-[13px] text-ink-400 md:flex-row">
          <span className="font-semibold">© 조목조목</span>
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
    <div className="h-full rounded-3xl bg-white p-7 shadow-card transition-all duration-200 hover:-translate-y-1.5 hover:shadow-float">
      <span className="text-[28px]">{emoji}</span>
      <p className="mt-4 text-[17px] font-bold text-ink-900">{title}</p>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-400">{body}</p>
    </div>
  )
}

function Step({ no, title, body }: { no: string; title: string; body: string }) {
  return (
    <div className="h-full rounded-3xl border border-ink-100 p-7 transition-all duration-200 hover:-translate-y-1.5 hover:border-brand-500/30 hover:shadow-card">
      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 text-[15px] font-extrabold text-brand-600">
        {no}
      </span>
      <p className="mt-4 text-[17px] font-bold text-ink-900">{title}</p>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-400">{body}</p>
    </div>
  )
}
