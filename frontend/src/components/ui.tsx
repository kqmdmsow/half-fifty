import { useCallback, useState, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { RISK_META, type RiskLevel } from '../data/sample'

/* ---------- Button ---------- */

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

const BUTTON_STYLE: Record<ButtonVariant, string> = {
  primary:
    'bg-brand-500 text-white hover:bg-brand-600 active:bg-brand-700 disabled:bg-ink-100 disabled:text-ink-300',
  secondary:
    'bg-ink-50 text-ink-700 hover:bg-ink-100 active:bg-ink-100 disabled:text-ink-300',
  ghost:
    'bg-transparent text-ink-600 hover:bg-ink-50 active:bg-ink-100 disabled:text-ink-300',
  danger: 'bg-danger-50 text-danger-600 hover:bg-danger-50/80 active:bg-danger-50',
}

export function Button({
  variant = 'primary',
  size = 'md',
  full = false,
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: 'sm' | 'md' | 'lg'
  full?: boolean
}) {
  // KRDS 터치 타깃: 모든 크기가 최소 48px(--krds-size-height-7) — sm도 h-12
  const sizeStyle =
    size === 'lg'
      ? 'h-14 px-7 text-[17px]'
      : size === 'sm'
        ? 'h-12 px-4 text-sm'
        : 'h-12 px-5 text-[15px]'

  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-1.5 rounded-2xl font-semibold transition-colors duration-150 disabled:cursor-not-allowed ${sizeStyle} ${BUTTON_STYLE[variant]} ${full ? 'w-full' : ''} ${className}`}
      {...props}
    />
  )
}

/* ---------- Risk badge ---------- */

// 위험도 3중 인코딩(KRDS 접근성 원칙): 색 + 아이콘 + 텍스트 — 색만으로
// 구분하지 않는다 (색각 이상·고대비 모드에서도 위험도가 즉시 구분되도록).
const RISK_ICON: Record<RiskLevel, ReactNode> = {
  위험: (
    // 삼각형 느낌표
    <svg aria-hidden viewBox="0 0 16 16" className="h-3.5 w-3.5 shrink-0 fill-current">
      <path d="M8 1.5 15.2 14a.9.9 0 0 1-.78 1.35H1.58A.9.9 0 0 1 .8 14L8 1.5Zm-.75 4.7v4.3h1.5V6.2h-1.5Zm0 5.5v1.6h1.5v-1.6h-1.5Z" />
    </svg>
  ),
  주의: (
    // 원형 느낌표
    <svg aria-hidden viewBox="0 0 16 16" className="h-3.5 w-3.5 shrink-0 fill-current">
      <path d="M8 1a7 7 0 1 1 0 14A7 7 0 0 1 8 1Zm-.75 3.5v5h1.5v-5h-1.5Zm0 6.2v1.6h1.5v-1.6h-1.5Z" />
    </svg>
  ),
  안전: (
    // 원형 체크
    <svg aria-hidden viewBox="0 0 16 16" className="h-3.5 w-3.5 shrink-0 fill-current">
      <path d="M8 1a7 7 0 1 1 0 14A7 7 0 0 1 8 1Zm3.1 4.6-4 4.2-1.9-1.9-1.1 1.1 3 3 5.1-5.3-1.1-1.1Z" />
    </svg>
  ),
}

// 배지 밖(내비 칩·계산기 등)에서도 같은 아이콘을 쓰도록 공개
export function RiskIcon({ level, className = '' }: { level: RiskLevel; className?: string }) {
  return <span className={`inline-flex ${className}`}>{RISK_ICON[level]}</span>
}

export function RiskBadge({
  level,
  label,
  className = '',
}: {
  level: RiskLevel
  label?: string // 다국어 라벨 오버라이드 (i18n.riskLevelLabel)
  className?: string
}) {
  const meta = RISK_META[level]
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1 text-[13px] font-bold ${meta.badge} ${className}`}
    >
      {RISK_ICON[level]}
      {label ?? meta.label}
    </span>
  )
}

/* ---------- 방화벽 상태 배지 (#174) ---------- */

/**
 * 판정 보류 배지 — '주의'보다 강하게 보여야 한다.
 *
 * 조용히 넘어가면 공격자가 조항 뒤에 지시문 한 줄을 붙이는 것만으로 경고를
 * 억제할 수 있다. 판정을 못 하겠다는 상태가 사용자에게 '주의'보다 약하게
 * 읽히면 fail-closed 설계 자체가 공격 수단이 된다.
 */
export function WithheldBadge({ label, className = '' }: { label: string; className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg border-2 border-danger-500 bg-danger-50 px-2.5 py-1 text-[13px] font-bold text-danger-600 ${className}`}
    >
      <svg aria-hidden viewBox="0 0 16 16" className="h-3.5 w-3.5 shrink-0 fill-current">
        {/* 물음표 방패 — "막았지만 답을 못 냈다" */}
        <path d="M8 .8 2 3v5.1c0 3.4 2.5 6.3 6 7.1 3.5-.8 6-3.7 6-7.1V3L8 .8Zm-.8 11.6v-1.5h1.6v1.5H7.2Zm2.5-5c-.3.4-.7.7-1 .9-.3.2-.4.4-.4.7v.4H6.9v-.6c0-.6.3-1.1.9-1.5.4-.3.7-.5.7-.9 0-.5-.4-.8-.9-.8-.5 0-.9.3-1 .9l-1.3-.3C5.5 5.2 6.4 4.5 7.7 4.5c1.3 0 2.2.7 2.2 1.9 0 .4-.1.7-.2 1Z" />
      </svg>
      {label}
    </span>
  )
}

/** 조작 탐지·격리 칩 — 방어가 동작했다는 사실 자체를 보여 준다. */
export function FirewallChip({ label, className = '' }: { label: string; className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-md bg-ink-100 px-2 py-0.5 text-[12px] font-semibold text-ink-600 ${className}`}
    >
      <svg aria-hidden viewBox="0 0 16 16" className="h-3 w-3 shrink-0 fill-current">
        <path d="M8 .8 2 3v5.1c0 3.4 2.5 6.3 6 7.1 3.5-.8 6-3.7 6-7.1V3L8 .8Zm2.9 5.3-3.6 3.8-2-2 1-1.1 1 1 2.6-2.7 1 1Z" />
      </svg>
      {label}
    </span>
  )
}

/* ---------- Switch (토글) ---------- */

export function Switch({
  checked,
  label,
  description,
  onChange,
}: {
  checked: boolean
  label: string
  description?: string
  onChange: () => void
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className="flex w-full items-center justify-between gap-4 rounded-2xl px-4 py-3.5 text-left transition-colors hover:bg-ink-25"
    >
      <span>
        <span className="block text-[15px] font-semibold text-ink-900">{label}</span>
        {description && <span className="mt-0.5 block text-[13px] text-ink-400">{description}</span>}
      </span>
      <span
        className={`relative h-7 w-12 shrink-0 rounded-full transition-colors duration-200 ${checked ? 'bg-brand-500' : 'bg-ink-200'}`}
      >
        <span
          className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow-sm transition-transform duration-200 ${checked ? 'translate-x-[22px]' : 'translate-x-0.5'}`}
        />
      </span>
    </button>
  )
}

/* ---------- Copy button ---------- */

export function CopyButton({
  text,
  children = '복사',
  copiedText = '복사됨',
  className = '',
}: {
  text: string
  children?: ReactNode
  copiedText?: string
  className?: string
}) {
  const [copied, setCopied] = useState(false)

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      /* clipboard 미지원 환경 무시 */
    }
  }, [text])

  return (
    <button
      type="button"
      onClick={copy}
      className={`shrink-0 rounded-lg px-2.5 py-1.5 text-[13px] font-bold transition-colors ${
        copied ? 'bg-safe-50 text-safe-700' : 'bg-brand-50 text-brand-600 hover:bg-brand-100'
      } ${className}`}
    >
      {copied ? copiedText : children}
    </button>
  )
}

/* ---------- Section title ---------- */

export function PageTitle({
  title,
  desc,
  align = 'left',
}: {
  title: ReactNode
  desc?: ReactNode
  align?: 'left' | 'center'
}) {
  return (
    <div className={align === 'center' ? 'text-center' : ''}>
      <h1 className="text-[26px] font-bold leading-snug tracking-[-0.02em] text-ink-900 md:text-[30px]">
        {title}
      </h1>
      {desc && <p className="mt-2.5 text-[15px] leading-relaxed text-ink-400">{desc}</p>}
    </div>
  )
}

/* ---------- Card ---------- */

export function Card({
  children,
  className = '',
  interactive = false,
  onClick,
}: {
  children: ReactNode
  className?: string
  interactive?: boolean
  onClick?: () => void
}) {
  if (interactive) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`block w-full rounded-3xl border border-ink-100 bg-white text-left shadow-card transition-all duration-150 hover:-translate-y-0.5 hover:shadow-float ${className}`}
      >
        {children}
      </button>
    )
  }
  return (
    <div className={`rounded-3xl border border-ink-100 bg-white shadow-card ${className}`}>
      {children}
    </div>
  )
}

/* ---------- Logo ---------- */

export function Logo({ onClick }: { onClick?: () => void }) {
  return (
    <button type="button" onClick={onClick} className="flex items-center gap-2.5">
      <span className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-brand-500 text-[15px] font-extrabold text-white">
        조
      </span>
      <span className="text-[17px] font-bold tracking-tight text-ink-900">조목조목</span>
    </button>
  )
}
