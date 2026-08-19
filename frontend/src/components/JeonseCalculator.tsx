import { useState } from 'react'
import { Card } from './ui'
import { t, type LangCode } from '../i18n'

/** 깡통전세 위험 계산기 (#63) — LLM 무관, 순수 프론트 계산.
 *
 * 임계값·승산비는 data/jeonse_risk_reference.json에서 복사한 상수다
 * (frontend는 레포 루트 data/를 import할 수 없어 출처 주석으로 대신 연결):
 * 안선영·이상엽(2025) 수도권 전세보증 453,122건 이항로짓 + HUG 담보인정비율
 * 90% 인하(2023). 부채비율 = (선순위채권 + 전세보증금) / 주택가격.
 */
// 원문 표10 대조 검증(2026-08-19): Exp(B) 29.923/5.489/2.590/1.508,
// 준거변수는 부채비율 60% 미만 — <70%를 기준으로 뭉개면 60~70 구간의
// 1.5배가 누락되므로 논문 그대로 5구간을 쓴다.
const THRESHOLDS = [
  { min: 0.9, odds: 29.9, labelKey: 'jcG1', adviceKey: 'jcG1Advice', tone: 'danger' },
  { min: 0.8, odds: 5.5, labelKey: 'jcG2', adviceKey: 'jcG2Advice', tone: 'danger' },
  { min: 0.7, odds: 2.6, labelKey: 'jcG3', adviceKey: 'jcG3Advice', tone: 'caution' },
  { min: 0.6, odds: 1.5, labelKey: 'jcG5', adviceKey: 'jcG5Advice', tone: 'safe' },
  { min: 0, odds: 1.0, labelKey: 'jcG4', adviceKey: 'jcG4Advice', tone: 'safe' },
] as const

const TONE_STYLE = {
  danger: { box: 'bg-danger-50 border-danger-500/20', badge: 'bg-danger-500 text-white', text: 'text-danger-600' },
  caution: { box: 'bg-caution-50 border-caution-500/20', badge: 'bg-caution-500 text-white', text: 'text-caution-700' },
  safe: { box: 'bg-safe-50 border-safe-500/20', badge: 'bg-safe-500 text-white', text: 'text-safe-700' },
} as const

function parseAmount(value: string): number {
  const n = Number(value.replace(/[,\s]/g, ''))
  return Number.isFinite(n) && n >= 0 ? n : 0
}

export function JeonseCalculator({ language = 'ko' }: { language?: LangCode }) {
  const [deposit, setDeposit] = useState('')
  const [price, setPrice] = useState('')
  const [senior, setSenior] = useState('')

  const depositN = parseAmount(deposit)
  const priceN = parseAmount(price)
  const seniorN = parseAmount(senior)

  const ready = depositN > 0 && priceN > 0
  const ratio = ready ? (seniorN + depositN) / priceN : null
  const grade = ratio === null ? null : THRESHOLDS.find((g) => ratio >= g.min) ?? THRESHOLDS[THRESHOLDS.length - 1]

  const field = (
    labelKey: 'jcDeposit' | 'jcPrice' | 'jcSenior',
    value: string,
    onChange: (v: string) => void,
  ) => (
    <label className="block">
      <span className="text-[13px] font-semibold text-ink-600">{t(language, labelKey)}</span>
      <span className="relative mt-1.5 block">
        <input
          type="text"
          inputMode="numeric"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="0"
          className="w-full rounded-xl border border-ink-100 bg-white px-3.5 py-2.5 pr-14 text-[15px] font-semibold text-ink-900 outline-none placeholder:text-ink-200 focus:border-brand-500 focus:ring-2 focus:ring-brand-50"
        />
        <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[12px] font-bold text-ink-300">
          {t(language, 'jcUnit')}
        </span>
      </span>
    </label>
  )

  return (
    <Card className="px-5 py-5">
      <p className="text-[15px] font-bold text-ink-900">🏠 {t(language, 'jcTitle')}</p>
      <p className="mt-1 text-[13px] leading-relaxed text-ink-400">{t(language, 'jcDesc')}</p>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {field('jcDeposit', deposit, setDeposit)}
        {field('jcPrice', price, setPrice)}
        {field('jcSenior', senior, setSenior)}
      </div>

      {grade && ratio !== null ? (
        <div className={`mt-4 rounded-2xl border p-4 ${TONE_STYLE[grade.tone].box}`}>
          <div className="flex flex-wrap items-center gap-2.5">
            <span className={`rounded-lg px-2.5 py-1 text-[13px] font-bold ${TONE_STYLE[grade.tone].badge}`}>
              {t(language, grade.labelKey)}
            </span>
            <span className="text-[22px] font-bold text-ink-900">{(ratio * 100).toFixed(1)}%</span>
            <span className="text-[12px] font-semibold text-ink-400">{t(language, 'jcRatio')}</span>
          </div>
          {grade.odds > 1 && (
            <p className={`mt-2 text-[13px] font-bold ${TONE_STYLE[grade.tone].text}`}>
              {t(language, 'jcOdds', { x: grade.odds })}
            </p>
          )}
          <p className="mt-2 text-[14px] leading-relaxed text-ink-700">
            {t(language, grade.adviceKey)}
          </p>
        </div>
      ) : (
        <p className="mt-4 rounded-2xl bg-ink-25 px-4 py-3 text-[13px] font-semibold text-ink-400">
          {t(language, 'jcHint')}
        </p>
      )}

      <p className="mt-3 text-[11px] leading-relaxed text-ink-300">
        {t(language, 'jcSource')}
        <br />
        {t(language, 'jcNote')}
      </p>
    </Card>
  )
}
