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
// 원문 표10 대조 검증(2026-08-19): 승산비 Exp(B) 29.923/5.489/2.590/1.508,
// 준거변수는 부채비율 60% 미만. rate는 표6 원자료(구간 내 사고건수/총건수)로
// 직접 계산한 실측 사고율(%) — 표6의 '사고율' 컬럼은 전체 표본 대비 비율이라
// 그대로 쓰면 오독이다(합계를 표3과 대조해 검증). UI에는 일반 사용자가
// 직관적으로 이해하는 실측 사고율을 쓰고, 승산비(odds)는 근거 기록용으로 유지.
const THRESHOLDS = [
  { min: 0.9, odds: 29.9, rate: 17.6, labelKey: 'jcG1', adviceKey: 'jcG1Advice', tone: 'danger' },
  { min: 0.8, odds: 5.5, rate: 2.0, labelKey: 'jcG2', adviceKey: 'jcG2Advice', tone: 'danger' },
  { min: 0.7, odds: 2.6, rate: 0.8, labelKey: 'jcG3', adviceKey: 'jcG3Advice', tone: 'caution' },
  { min: 0.6, odds: 1.5, rate: 0.4, labelKey: 'jcG5', adviceKey: 'jcG5Advice', tone: 'safe' },
  { min: 0, odds: 1.0, rate: 0.2, labelKey: 'jcG4', adviceKey: 'jcG4Advice', tone: 'safe' },
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

// 위험 가중 요인 (표10 Exp(B), 부채비율과 같은 단일 모형의 조정 승산비)
const RISK_FACTORS = [
  { key: 'corp', labelKey: 'jcFCorp', odds: 3.6 },
  { key: 'multi', labelKey: 'jcFMulti', odds: 5.8 },
  { key: 'offi', labelKey: 'jcFOffi', odds: 2.3 },
  { key: 'appraisal', labelKey: 'jcFAppraisal', odds: 4.8 },
  { key: 'region', labelKey: 'jcFRegion', odds: 7.0 },
] as const

export function JeonseCalculator({ language = 'ko' }: { language?: LangCode }) {
  const [deposit, setDeposit] = useState('')
  const [price, setPrice] = useState('')
  const [senior, setSenior] = useState('')
  const [factors, setFactors] = useState<Set<string>>(new Set())

  const toggleFactor = (key: string) =>
    setFactors((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })

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
      <p className="text-[15px] font-bold text-ink-900"><span aria-hidden>🏠</span> {t(language, 'jcTitle')}</p>
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
          {grade.min > 0 && (
            <p className={`mt-2 text-[13px] font-bold ${TONE_STYLE[grade.tone].text}`}>
              {t(language, 'jcRate', { rate: grade.rate })}
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

      {/* 위험 가중 요인 체크 (①) — 부채비율과 별개로 사기 다발 조건을 표시 */}
      <div className="mt-4 rounded-2xl bg-ink-25 px-4 py-3.5">
        <p className="text-[13px] font-bold text-ink-700">{t(language, 'jcFactorTitle')}</p>
        <div className="mt-2.5 grid gap-1.5 md:grid-cols-2">
          {RISK_FACTORS.map((f) => (
            <label key={f.key} className="flex cursor-pointer items-center gap-2 text-[13px] text-ink-600">
              <input
                type="checkbox"
                checked={factors.has(f.key)}
                onChange={() => toggleFactor(f.key)}
                className="h-4 w-4 shrink-0 cursor-pointer rounded border-ink-200 accent-brand-500"
              />
              <span className="min-w-0 flex-1">{t(language, f.labelKey)}</span>
              <span className="shrink-0 rounded bg-danger-50 px-1.5 py-0.5 text-[11px] font-bold text-danger-600">
                ×{f.odds}
              </span>
            </label>
          ))}
        </div>
        {factors.size > 0 && (
          <p className="mt-2.5 rounded-xl bg-danger-50 px-3 py-2 text-[13px] font-bold text-danger-600">
            <span aria-hidden>⚠️</span> {t(language, 'jcFactorWarn', { n: factors.size })}
          </p>
        )}
      </div>

      {/* HUG 보증 가입 유도 (④) — 부채비율 90% 이하일 때만 (초과 구간은 가입 불가) */}
      {ratio !== null && ratio <= 0.9 && (
        <div className="mt-3 flex flex-col gap-2.5 rounded-2xl bg-safe-50 px-4 py-3.5 md:flex-row md:items-center md:justify-between">
          <p className="text-[13px] leading-relaxed text-safe-700"><span aria-hidden>🛡️</span> {t(language, 'jcHugOk')}</p>
          <a
            href="https://www.khug.or.kr/hug/web/ig/dr/igdr000001.jsp"
            target="_blank"
            rel="noreferrer"
            className="shrink-0 rounded-xl bg-safe-500 px-3.5 py-2 text-center text-[13px] font-bold text-white"
          >
            {t(language, 'jcHugBtn')} →
          </a>
        </div>
      )}

      <p className="mt-3 text-[11px] leading-relaxed text-ink-300">
        {t(language, 'jcSource')}
        <br />
        {t(language, 'jcNote')}
      </p>
    </Card>
  )
}
