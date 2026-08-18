import { useRef, useState, type DragEvent } from 'react'
import { Button, Card, PageTitle } from '../components/ui'

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
  onModeChange,
  onFileChange,
  onTextChange,
  onDomainChange,
  onNext,
}: {
  mode: InputMode
  file: File | null
  text: string
  domain: string
  onModeChange: (mode: InputMode) => void
  onFileChange: (file: File | null) => void
  onTextChange: (text: string) => void
  onDomainChange: (domain: string) => void
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
      setFileError('PDF 또는 사진(JPG·PNG·WEBP)만 올릴 수 있어요.')
      return
    }
    if (candidate.size > MAX_SIZE) {
      setFileError('파일이 10MB를 넘어요. 더 작은 파일로 올려주세요.')
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
        title="분석할 계약서를 올려주세요"
        desc="PDF는 물론 휴대폰으로 찍은 계약서 사진(JPG·PNG)도 돼요. 분석이 끝나면 원본은 즉시 삭제돼요."
      />

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
            {item === 'pdf' ? '파일·사진 업로드' : '직접 붙여넣기'}
          </button>
        ))}
      </div>

      <div className="mt-4">
        {mode === 'pdf' ? (
          <div
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(event) => event.key === 'Enter' && inputRef.current?.click()}
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
                  {(file.size / 1024 / 1024).toFixed(1)}MB · 클릭해서 다른 파일로 바꾸기
                </p>
              </>
            ) : (
              <>
                <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-[26px]">
                  📎
                </span>
                <p className="mt-4 text-[16px] font-bold text-ink-900">
                  PDF나 계약서 사진을 끌어다 놓거나 클릭하세요
                </p>
                <p className="mt-1 text-[13px] text-ink-400">
                  PDF·JPG·PNG·WEBP · 최대 10MB · 스캔본도 읽을 수 있어요
                </p>
              </>
            )}
          </div>
        ) : (
          <textarea
            className="min-h-64 w-full resize-y rounded-3xl border border-ink-100 bg-white p-5 text-[15px] leading-relaxed text-ink-900 shadow-card outline-none placeholder:text-ink-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-50"
            placeholder="계약서 내용을 붙여넣어 주세요. (30자 이상)"
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
        <p className="text-[14px] font-bold text-ink-900">어떤 계약서인가요?</p>
        <p className="mt-1 text-[13px] leading-relaxed text-ink-400">
          유형을 알려주시면 더 정확해져요. 예를 들어 같은 "2기 연체 시 해지" 조항도
          주택이면 표준, 상가면 위험이에요. 몰라도 괜찮아요.
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
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
            잘 모르겠어요
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
                {item}
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
            분석을 위한 일시적 문서 처리에 동의합니다.{' '}
            <span className="text-ink-400">
              원문은 AI 학습에 사용하지 않으며 분석 완료 후 삭제돼요.
            </span>
          </span>
        </label>
      </Card>

      <Button size="lg" full className="mt-6" disabled={!ready} onClick={onNext}>
        {ready ? '다음' : mode === 'pdf' ? '계약서를 올려주세요' : '내용을 입력해 주세요'}
      </Button>
    </div>
  )
}
