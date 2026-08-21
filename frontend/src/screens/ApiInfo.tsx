import { Button, Card } from '../components/ui'
import { t, type LangCode } from '../i18n'

/** 제휴·API 안내 (#85 BM v1) — 가격표 없는 소개 + 문의 CTA.
 *
 * 팀 결정(#85): 제출 전에 실체 없는 가격을 공개하면 심사 공격 여지가 있어
 * v1은 "무엇을 제공하는가 + 도입 문의"까지만. 과금 문안은 §6-1 확정 후.
 * 대상이 사업자(B2B)라 ko/en만 실번역하고 나머지 언어는 영어 폴백(i18n 주석).
 */
export function ApiInfoScreen({
  language = 'ko',
  onBack,
}: {
  language?: LangCode
  onBack: () => void
}) {
  const point = (titleKey: Parameters<typeof t>[1], bodyKey: Parameters<typeof t>[1]) => (
    <Card className="p-6">
      <p className="text-[16px] font-bold text-ink-900">{t(language, titleKey)}</p>
      <p className="mt-1.5 text-[14px] leading-relaxed text-ink-600">{t(language, bodyKey)}</p>
    </Card>
  )

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="text-[26px] font-bold leading-snug tracking-[-0.02em] text-ink-900 md:text-[30px]">
        {t(language, 'apiTitle')}
      </h1>
      <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-ink-600">
        {t(language, 'apiSubtitle')}
      </p>

      {/* 왜 이 API인가 — 서비스 차별점이 그대로 상품성 */}
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {point('apiPoint1Title', 'apiPoint1Body')}
        {point('apiPoint2Title', 'apiPoint2Body')}
        {point('apiPoint3Title', 'apiPoint3Body')}
      </div>

      {/* 사용처 */}
      <h2 className="mt-12 text-[19px] font-bold text-ink-900">{t(language, 'apiUseTitle')}</h2>
      <ul className="mt-4 space-y-2.5">
        {(['apiUse1', 'apiUse2', 'apiUse3'] as const).map((key) => (
          <li key={key} className="flex items-start gap-2.5 text-[15px] leading-relaxed text-ink-700">
            <span aria-hidden className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
            {t(language, key)}
          </li>
        ))}
      </ul>

      {/* 실제 엔드포인트 예시 — 데모 서비스가 지금 쓰는 것과 동일 계약 */}
      <h2 className="mt-12 text-[19px] font-bold text-ink-900">{t(language, 'apiHowTitle')}</h2>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-600">{t(language, 'apiHowBody')}</p>
      <pre className="mt-4 overflow-x-auto rounded-2xl bg-ink-900 p-5 text-[13px] leading-relaxed text-ink-50">
        <code>{`POST /api/contracts/analyze-stream
Content-Type: application/json

{"text": "제3조(위약금) ...", "persona": "adult", "language": "ko"}

→ NDJSON 스트림: meta → clause(조항별 판정·근거·확인질문)
  → judge(검증 점수) → done`}</code>
      </pre>

      {/* 도입 단계 — 가격 없음 */}
      <h2 className="mt-12 text-[19px] font-bold text-ink-900">{t(language, 'apiStageTitle')}</h2>
      <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-ink-600">{t(language, 'apiStageBody')}</p>

      {/* 법적 고지 + CTA */}
      <Card className="mt-10 bg-ink-25 p-6">
        <p className="text-[13px] leading-relaxed text-ink-600">{t(language, 'apiLegal')}</p>
        <div className="mt-5 flex flex-col gap-3 md:flex-row md:items-center">
          <a
            href="https://github.com/kqmdmsow/half-fifty/issues"
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-12 items-center justify-center rounded-2xl bg-brand-500 px-6 text-[15px] font-semibold text-white hover:bg-brand-600"
          >
            {t(language, 'apiContactCta')} →
          </a>
          <Button variant="secondary" onClick={onBack}>
            {t(language, 'apiBack')}
          </Button>
        </div>
      </Card>
    </div>
  )
}
