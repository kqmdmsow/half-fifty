import { Button, RiskBadge } from '../components/ui'
import { Reveal } from '../components/Reveal'
import { RotatingTitle } from '../components/RotatingTitle'
import { LANGUAGES, riskLevelLabel, t, type LangCode } from '../i18n'
import { VERIFICATION } from '../data/verification'

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
      {/* Hero — 중앙 정렬 + 회전 헤드라인 + 실물 계약서 목업 (#134 리디자인) */}
      <section className="relative overflow-hidden">
        {/* 배경 광원 — KRDS brand-50 토큰의 블러 원 (장식) */}
        <div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-[-160px] -z-10 h-[460px] w-[780px] -translate-x-1/2 rounded-full bg-brand-50 opacity-70 blur-3xl"
        />
        <div className="hero-stagger mx-auto max-w-3xl px-6 pt-16 text-center md:pt-24">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3.5 py-1.5 text-[13px] font-bold text-brand-600">
            {t(language, 'heroBadge')}
          </span>
          <h1 className="mt-7 text-[38px] font-bold leading-[1.22] tracking-[-0.02em] text-ink-900 md:text-[58px]">
            <RotatingTitle language={language} />
          </h1>
          <p className="mx-auto mt-5 max-w-md text-[17px] leading-relaxed text-ink-600">
            {t(language, 'landingSubtitle')}
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-4">
            <Button size="lg" onClick={onStart}>
              {t(language, 'landingCta')}
            </Button>
            <span className="text-[13px] font-medium text-ink-400">
              {t(language, 'heroNote')}
            </span>
          </div>

          {/* 신뢰 지표 (#169) — 심사위원·사용자가 분석을 돌리기 전에 "왜 이 판정을
              믿나"를 볼 수 있게 한다. 결과 화면의 AI 검증 리포트(#53)·사건
              각주(#91)는 분석을 끝까지 돌려야 보이는데, 그 전에 이탈하면 우리
              강점이 전달되지 않는다. 숫자는 data/verification.ts가 단일 출처. */}
          <ul
            aria-label={t(language, 'trAria')}
            className="mx-auto mt-8 flex max-w-2xl flex-wrap items-center justify-center gap-x-2.5 gap-y-2 text-[13px] font-semibold text-ink-500"
          >
            {[
              t(language, 'trGolden', { n: VERIFICATION.goldenRows }),
              t(language, 'trNormalFp', { n: VERIFICATION.normalClauses }),
              t(language, 'trJudge', { n: VERIFICATION.judgeFamilies }),
            ].map((label) => (
              <li
                key={label}
                className="rounded-full border border-ink-100 bg-white/70 px-3.5 py-1.5"
              >
                {label}
              </li>
            ))}
          </ul>
        </div>

        {/* 실물 계약서 목업 — 국토부·법무부 표준계약서 실제 문안 + 법 조항 칩.
            주의: 칩·카드 위치는 transform이 아니라 left/right 오프셋으로 —
            float 애니메이션이 transform을 덮어쓰기 때문 (실측 버그). */}
        {/* 장식이므로 스크린리더에서 통째로 제외 (#82 2차 결정 유지) —
            가짜 파일명·위험 배지가 실제 결과처럼 낭독되면 혼란만 준다 */}
        <div aria-hidden className="relative mx-auto mt-10 w-full max-w-2xl px-6 pb-24">
          <div className="relative">
            {/* 뒷장 — 종이 크기에 맞춤 (컨테이너 h-full이면 아래로 길게 샘) */}
            <div
              aria-hidden
              className="absolute inset-x-6 inset-y-0 translate-y-3 rotate-2 rounded-xl border border-ink-100 bg-white shadow-card"
            />
            {/* 본장 */}
            <div className="animate-float relative -rotate-1 rounded-xl border border-ink-200 bg-white p-7 shadow-float md:p-10">
              <p className="text-center text-[18px] font-bold tracking-[0.25em] text-ink-900 md:text-[20px]">
                주택임대차 표준계약서
              </p>
              <p className="mt-1.5 text-center text-[11px] text-ink-400">
                법무부 · 국토교통부 · 서울시 공동 서식 — 실제 문안
              </p>
              <div className="mt-7 space-y-3.5 text-left text-[13px] leading-relaxed text-ink-600">
                <p>
                  <b className="text-ink-900">제2조(임대차기간)</b> 임대인은 임차주택을 임대차
                  목적대로 사용·수익할 수 있는 상태로 임차인에게 인도하고, 임대차기간은
                  인도일로부터 정한 날까지로 한다.
                </p>
                <p>
                  <b className="text-ink-900">제3조(입주 전 수리)</b> 임대인과 임차인은
                  임차주택의 수리가 필요한 시설물 및 비용부담에 관하여 합의한다.
                </p>
                <p>
                  <b className="text-ink-900">특약사항</b>{' '}
                  <span className="bg-[linear-gradient(transparent_55%,rgb(var(--c-danger-50))_55%)] font-semibold text-ink-900 underline decoration-danger-500 decoration-wavy decoration-2 underline-offset-4">
                    "계약 종료 후 3개월 이내에 보증금을 반환할 수 있다."
                  </span>
                </p>
              </div>
              {/* 도장 (장식) */}
              <div
                aria-hidden
                className="absolute bottom-5 right-6 flex h-[70px] w-[70px] rotate-12 items-center justify-center rounded-full border-[3px] border-danger-500/60 text-center text-[14px] font-extrabold leading-tight text-danger-500/70"
              >
                조목
                <br />
                조목
              </div>
            </div>

            {/* 법 조항 칩 — 실제 근거 법령 (lg 이상, 장식). 종이 밖에 완전히 배치 */}
            <div aria-hidden className="absolute right-full top-24 mr-4 hidden lg:block">
              <div className="animate-float-delay whitespace-nowrap rounded-full border border-ink-100 bg-white px-4 py-2.5 text-[12px] font-bold text-ink-600 shadow-card">
                주택임대차보호법 제3조의2
              </div>
            </div>
            <div aria-hidden className="absolute left-full top-10 ml-4 hidden lg:block">
              <div className="animate-float whitespace-nowrap rounded-full border border-ink-100 bg-white px-4 py-2.5 text-[12px] font-bold text-ink-600 shadow-card">
                민법 제623조
              </div>
            </div>
            <div aria-hidden className="absolute bottom-24 left-full ml-4 hidden lg:block">
              <div className="animate-float-delay whitespace-nowrap rounded-full border border-ink-100 bg-white px-4 py-2.5 text-[12px] font-bold text-ink-600 shadow-card">
                상가건물 임대차보호법 제10조
              </div>
            </div>

            {/* 위험 경고 카드 — 종이 하단에 살짝 겹치게 */}
            <div className="absolute -bottom-12 right-2 w-72 rounded-2xl border border-ink-100 bg-white p-5 shadow-float md:right-6">
              <RiskBadge level="위험" label={riskLevelLabel(language, '위험')} />
              <p className="mt-2 text-[15px] font-bold text-ink-900">{t(language, 'mockTitle')}</p>
              <p className="mt-1.5 text-[13px] leading-relaxed text-ink-400">
                {t(language, 'mockBody')}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 지원 언어 마퀴 (#134 모션) — 장식이므로 스크린리더에서 제외,
          reduced-motion에서는 애니메이션이 정지돼 첫 화면 분량만 보인다 */}
      <div aria-hidden className="overflow-hidden border-t border-ink-50 py-5 [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
        <div className="flex w-max animate-marquee">
          {[...LANGUAGES, ...LANGUAGES].map((item, i) => (
            <span
              key={`${item.id}-${i}`}
              className="mr-3 whitespace-nowrap rounded-full bg-ink-50 px-4 py-2 text-[13px] font-bold text-ink-600"
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
                ['feat1Title', 'feat1Body'],
                ['feat2Title', 'feat2Body'],
                ['feat3Title', 'feat3Body'],
                ['feat4Title', 'feat4Body'],
              ] as const
            ).map(([titleKey, bodyKey], i) => (
              <Reveal key={titleKey} delay={i * 90}>
                <Feature title={t(language, titleKey)} body={t(language, bodyKey)} />
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

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div className="h-full rounded-3xl bg-white p-7 shadow-card transition-all duration-200 hover:-translate-y-1.5 hover:shadow-float">
      <p className="text-[17px] font-bold text-ink-900">{title}</p>
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
      <p className="text-[17px] font-bold text-ink-900">{title}</p>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-400">{body}</p>
    </div>
  )
}
