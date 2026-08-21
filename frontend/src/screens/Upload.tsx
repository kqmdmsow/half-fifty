import { useRef, useState, type DragEvent } from 'react'
import { Button, Card, PageTitle } from '../components/ui'
import { domainLabel, riskLevelLabel, t, type LangCode } from '../i18n'
import { DEMO_SAMPLES, type DemoSample } from '../data/samples'

type InputMode = 'pdf' | 'text'

const MAX_SIZE = 10 * 1024 * 1024

// agent/src/nodes/domain.py의 ALLOWED_DOMAINS와 값이 정확히 일치해야 한다.
// 회의 안건 D: 문서 유형은 업로드 시 사용자 선택이 기본 (LLM 자동판별은 opt-in).
const DOMAINS = [
  '주택임대차', '상가임대차', '임대차(구분불명)', '대출·여신', '보험',
  '신용카드', '예금·수신', '투자·신탁', '가맹(프랜차이즈)', '상조·멤버십',
  '매매·분양', '근로계약', '기타',
]

const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const isImage = (f: File) =>
  IMAGE_TYPES.includes(f.type) || /\.(jpe?g|png|webp)$/i.test(f.name)
const isPdf = (f: File) =>
  f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')

export function UploadScreen({
  mode,
  file,
  text,
  domain,
  language = 'ko',
  onModeChange,
  onFileChange,
  onTextChange,
  onDomainChange,
  onSampleSelect,
  onNext,
}: {
  mode: InputMode
  file: File | null
  text: string
  domain: string
  language?: LangCode
  onModeChange: (mode: InputMode) => void
  onFileChange: (file: File | null) => void
  onTextChange: (text: string) => void
  onDomainChange: (domain: string) => void
  onSampleSelect: (sample: DemoSample) => void
  onNext: () => void
}) {
  const [agreed, setAgreed] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const acceptFile = (candidate: File | null) => {
    setFileError(null)
    if (!candidate) return
    if (!isPdf(candidate) && !isImage(candidate)) {
      setFileError(t(language, 'upErrType'))
      return
    }
    if (candidate.size > MAX_SIZE) {
      setFileError(t(language, 'upErrSize'))
      return
    }
    onFileChange(candidate)
  }

  const handleDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    acceptFile(event.dataTransfer.files?.[0] ?? null)
  }

  const ready = agreed && (mode === 'pdf' ? Boolean(file) : text.trim().length > 30)

  return (
    <div className="mx-auto max-w-xl animate-fade-up px-6 py-12 md:py-16">
      <PageTitle
        title={t(language, 'upTitle')}
        desc={t(language, 'upDesc')}
      />

      {/* 원클릭 데모 샘플 (#81) — 계약서가 없어도 버튼 하나로 체험 */}
      <Card className="mt-6 px-5 py-4">
        <p className="text-[14px] font-bold text-ink-900">{t(language, 'spTitle')}</p>
        <p className="mt-1 text-[13px] leading-relaxed text-ink-400">{t(language, 'spDesc')}</p>
        <div className="mt-3 grid gap-2 md:grid-cols-2" role="group" aria-label={t(language, 'spTitle')}>
          {DEMO_SAMPLES.map((sample) => (
            <button
              key={sample.id}
              type="button"
              onClick={() => onSampleSelect(sample)}
              className="flex items-center justify-between gap-2 rounded-xl bg-ink-25 px-3.5 py-2.5 text-left text-[13px] font-semibold text-ink-700 transition-colors hover:bg-brand-50 hover:text-brand-600"
            >
              <span className="min-w-0 flex-1">{t(language, sample.labelKey)}</span>
              <span
                className={`shrink-0 rounded-md px-1.5 py-0.5 text-[11px] font-bold ${
                  sample.expected === '위험'
                    ? 'bg-danger-50 text-danger-600'
                    : 'bg-safe-50 text-safe-700'
                }`}
              >
                {riskLevelLabel(language ?? 'ko', sample.expected)}
              </span>
            </button>
          ))}
        </div>
      </Card>

      {/* 스크린리더 전용 경로 안내 (#82) — 2025 금융위 정책으로 은행 계약서류가
          텍스트 파일로 제공되기 시작해, 붙여넣기가 시각장애인 주 경로다 */}
      <p className="sr-only">{t(language, 'upSrHint')}</p>

      {/* 입력 방식 탭 */}
      <div className="mt-8 grid grid-cols-2 rounded-2xl bg-ink-50 p-1">
        {(['pdf', 'text'] as InputMode[]).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => onModeChange(item)}
            className={`h-11 rounded-xl text-[15px] font-semibold transition-all ${
              mode === item ? 'bg-white text-ink-900 shadow-card' : 'text-ink-400 hover:text-ink-600'
            }`}
          >
            {item === 'pdf' ? t(language, 'upTabFile') : t(language, 'upTabText')}
          </button>
        ))}
      </div>

      <div className="mt-4">
        {mode === 'pdf' ? (
          <div
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                inputRef.current?.click()
              }
            }}
            onDragOver={(event) => {
              event.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={`flex cursor-pointer flex-col items-center rounded-3xl border-2 border-dashed px-6 py-14 text-center transition-colors ${
              dragging
                ? 'border-brand-500 bg-brand-50'
                : file
                  ? 'border-safe-500 bg-safe-50/40'
                  : 'border-ink-200 bg-ink-25 hover:border-brand-500 hover:bg-brand-50/50'
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(event) => acceptFile(event.target.files?.[0] ?? null)}
            />
            {file ? (
              <>
                <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-safe-50 text-[26px]">
                  {isImage(file) ? '📷' : '📄'}
                </span>
                <p className="mt-4 max-w-full truncate text-[16px] font-bold text-ink-900">
                  {file.name}
                </p>
                <p className="mt-1 text-[13px] text-ink-400">
                  {(file.size / 1024 / 1024).toFixed(1)}MB · {t(language, 'upFileChange')}
                </p>
              </>
            ) : (
              <>
                <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-[26px]">
                  📎
                </span>
                <p className="mt-4 text-[16px] font-bold text-ink-900">
                  {t(language, 'upDropTitle')}
                </p>
                <p className="mt-1 text-[13px] text-ink-400">
                  {t(language, 'upDropHint')}
                </p>
              </>
            )}
          </div>
        ) : (
          <textarea
            className="min-h-64 w-full resize-y rounded-3xl border border-ink-100 bg-white p-5 text-[15px] leading-relaxed text-ink-900 shadow-card outline-none placeholder:text-ink-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-50"
            placeholder={t(language, 'upPlaceholder')}
            value={text}
            onChange={(event) => onTextChange(event.target.value)}
          />
        )}
        {fileError && (
          <p className="mt-3 rounded-2xl bg-danger-50 px-4 py-3 text-[14px] font-semibold text-danger-600">
            {fileError}
          </p>
        )}
      </div>

      {/* 문서 유형 선택 — 유형에 따라 판정이 갈리는 조항(예: 2기 연체 해지)이 있어
          알려주면 더 정확해진다. 몰라도 분석은 가능 (조항 문언만으로 판단) */}
      <Card className="mt-4 px-5 py-4">
        <p className="text-[14px] font-bold text-ink-900">{t(language, 'upDomainTitle')}</p>
        <p className="mt-1 text-[13px] leading-relaxed text-ink-400">
          {t(language, 'upDomainDesc')}
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5" role="group" aria-label={t(language, 'upDomainTitle')}>
          <button
            type="button"
            aria-pressed={domain === ''}
            onClick={() => onDomainChange('')}
            className={`rounded-full px-3.5 py-2 text-[13px] font-semibold transition-colors ${
              domain === ''
                ? 'bg-ink-900 text-white'
                : 'bg-ink-50 text-ink-600 hover:bg-ink-100'
            }`}
          >
            {t(language, 'upDomainUnknown')}
          </button>
          {DOMAINS.map((item) => {
            const active = domain === item
            return (
              <button
                key={item}
                type="button"
                aria-pressed={active}
                onClick={() => onDomainChange(active ? '' : item)}
                className={`rounded-full px-3.5 py-2 text-[13px] font-semibold transition-colors ${
                  active
                    ? 'bg-brand-500 text-white'
                    : 'bg-ink-50 text-ink-600 hover:bg-ink-100'
                }`}
              >
                {domainLabel(language, item)}
              </button>
            )
          })}
        </div>
      </Card>

      {/* 동의 */}
      <Card className="mt-4 px-5 py-4">
        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(event) => setAgreed(event.target.checked)}
            className="mt-0.5 h-5 w-5 shrink-0 cursor-pointer rounded-md border-ink-200 accent-brand-500"
          />
          <span className="text-[14px] leading-relaxed text-ink-600">
            {t(language, 'upConsent')}{' '}
            <span className="text-ink-400">{t(language, 'upConsentSub')}</span>
          </span>
        </label>
      </Card>

      <Button size="lg" full className="mt-6" disabled={!ready} onClick={onNext}>
        {ready ? t(language, 'upNext') : mode === 'pdf' ? t(language, 'upNeedFile') : t(language, 'upNeedText')}
      </Button>
    </div>
  )
}
