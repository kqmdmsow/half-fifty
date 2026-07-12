import { useRef, useState, type DragEvent } from 'react'
import { Button, Card, PageTitle } from '../components/ui'

type InputMode = 'pdf' | 'text'

const MAX_SIZE = 10 * 1024 * 1024

export function UploadScreen({
  mode,
  file,
  text,
  onModeChange,
  onFileChange,
  onTextChange,
  onNext,
}: {
  mode: InputMode
  file: File | null
  text: string
  onModeChange: (mode: InputMode) => void
  onFileChange: (file: File | null) => void
  onTextChange: (text: string) => void
  onNext: () => void
}) {
  const [agreed, setAgreed] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const acceptFile = (candidate: File | null) => {
    setFileError(null)
    if (!candidate) return
    if (candidate.type !== 'application/pdf' && !candidate.name.toLowerCase().endsWith('.pdf')) {
      setFileError('PDF 파일만 올릴 수 있어요.')
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
        desc="텍스트를 읽을 수 있는 PDF를 지원해요. 분석이 끝나면 원본은 즉시 삭제돼요."
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
            {item === 'pdf' ? 'PDF 업로드' : '직접 붙여넣기'}
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
              accept="application/pdf"
              className="hidden"
              onChange={(event) => acceptFile(event.target.files?.[0] ?? null)}
            />
            {file ? (
              <>
                <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-safe-50 text-[26px]">
                  📄
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
                  PDF를 끌어다 놓거나 클릭하세요
                </p>
                <p className="mt-1 text-[13px] text-ink-400">최대 10MB · 최대 20페이지</p>
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
