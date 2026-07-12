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
  const sizeStyle =
    size === 'lg'
      ? 'h-14 px-7 text-[17px]'
      : size === 'sm'
        ? 'h-10 px-4 text-sm'
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

export function RiskBadge({ level, className = '' }: { level: RiskLevel; className?: string }) {
  const meta = RISK_META[level]
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1 text-[13px] font-bold ${meta.badge} ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
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
        하
      </span>
      <span className="text-[17px] font-bold tracking-tight text-ink-900">하프피프티</span>
    </button>
  )
}
