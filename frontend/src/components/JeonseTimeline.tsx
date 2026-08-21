import { useState } from 'react'
import { Card } from './ui'
import { t, type LangCode } from '../i18n'

/** 잔금일 안전 타임라인 (#63 확장 ③) — LLM 무관 프론트 전용.
 *
 * 전세사기의 대표 통로가 '대항력은 전입신고 다음 날 0시 발생'이라는 하루의
 * 틈(잔금일 당일 근저당 설정)이므로, 잔금일 기준 날짜별 필수 행동을
 * 달력 날짜로 박아서 보여준다. 임대차 도메인 결과 화면에서 계산기와 함께 노출.
 */
const LOCALE: Record<string, string> = {
  ko: 'ko-KR', en: 'en-US', zh: 'zh-CN', vi: 'vi-VN', th: 'th-TH', id: 'id-ID',
  tl: 'fil-PH', ne: 'ne-NP', km: 'km-KH', my: 'my-MM', mn: 'mn-MN', uz: 'uz-UZ',
  si: 'si-LK', bn: 'bn-BD', ru: 'ru-RU', ja: 'ja-JP',
}

export function JeonseTimeline({ language = 'ko' }: { language?: LangCode }) {
  const [date, setDate] = useState('')

  const base = date ? new Date(`${date}T00:00:00`) : null
  const fmt = (offsetDays: number) => {
    if (!base) return null
    const d = new Date(base)
    d.setDate(d.getDate() + offsetDays)
    return new Intl.DateTimeFormat(LOCALE[language] ?? 'ko-KR', {
      month: 'short', day: 'numeric', weekday: 'short',
    }).format(d)
  }

  const steps = [
    { offset: -1, key: 'jtBefore' as const },
    { offset: 0, key: 'jtDay' as const },
    { offset: 1, key: 'jtNext' as const },
    { offset: 7, key: 'jtLater' as const },
  ]

  return (
    <Card className="px-5 py-5">
      <p className="text-[15px] font-bold text-ink-900">{t(language, 'jtTitle')}</p>
      <p className="text-[15px] font-bold text-ink-900"><span aria-hidden>📅</span> {t(language, 'jtTitle')}</p>
      <p className="mt-1 text-[13px] leading-relaxed text-ink-400">{t(language, 'jtDesc')}</p>

      <label className="mt-4 block max-w-xs">
        <span className="text-[13px] font-semibold text-ink-600">{t(language, 'jtDate')}</span>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="mt-1.5 w-full rounded-xl border border-ink-100 bg-white px-3.5 py-2.5 text-[15px] font-semibold text-ink-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-50"
        />
      </label>

      {base && (
        <ol className="mt-4 space-y-2.5">
          {steps.map((step) => (
            <li key={step.key} className="flex gap-3 rounded-2xl bg-ink-25 px-4 py-3">
              <span
                aria-hidden
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-50 text-[13px] font-extrabold text-brand-600"
              >
                {steps.indexOf(step) + 1}
              </span>
              <div className="min-w-0">
                <p className="text-[12px] font-bold text-brand-600">{fmt(step.offset)}</p>
                <p className="mt-0.5 text-[13px] leading-relaxed text-ink-700">
                  {t(language, step.key)}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </Card>
  )
}
