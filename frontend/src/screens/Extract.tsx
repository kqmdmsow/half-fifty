import { Button, Card, PageTitle } from '../components/ui'

/** 파서(agent/src/nodes/parser.py)의 핵심 규칙을 미러링한 클라이언트 추정치.
 *  정확한 조항 수는 서버 파서가 결정하므로 어디까지나 '예상'으로만 표기한다. */
function estimateClauseCount(text: string): number {
  const matches = text.match(/^제\d+조(의\d+)?/gm)
  return matches?.length ?? 0
}

const MIN_TEXT_LENGTH = 30

export function ExtractScreen({
  file,
  mode,
  text,
  onPrev,
  onNext,
}: {
  file: File | null
  mode: 'pdf' | 'text'
  text: string
  onPrev: () => void
  onNext: () => void
}) {
  const isTextMode = mode === 'text' && text.trim().length > 0
  const docName = file?.name ?? (isTextMode ? '직접 입력한 내용' : '올린 파일')

  const clauseEstimate = isTextMode ? estimateClauseCount(text) : null
  const charCount = isTextMode ? text.trim().length : null
  const enoughText = isTextMode ? text.trim().length >= MIN_TEXT_LENGTH : true

  const isImage = file?.type.startsWith('image/') ?? false
  const fileSizeMb = file ? (file.size / 1024 / 1024).toFixed(1) : null

  return (
    <div className="mx-auto max-w-5xl animate-fade-up px-6 py-12 md:py-16">
      <PageTitle
        title={isTextMode ? '내용이 제대로 붙여넣어졌는지 확인해 주세요' : '올린 파일을 확인해 주세요'}
        desc={
          isTextMode
            ? '내용이 깨졌거나 빠졌다면 이전 화면에서 다시 붙여넣어 주세요.'
            : '파일 내용은 분석을 시작하면 서버에서 안전하게 추출돼요. 스캔본·사진도 OCR로 읽을 수 있어요.'
        }
      />

      <div className="mt-8 grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
        {/* 본문: 텍스트 모드는 실제 입력 내용, 파일 모드는 파일 안내 */}
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-ink-50 px-6 py-4">
            <p className="text-[15px] font-bold text-ink-900">
              {isTextMode ? '입력한 내용' : '올린 파일'}
            </p>
            <span className="max-w-52 truncate rounded-lg bg-ink-50 px-3 py-1 text-[13px] font-semibold text-ink-600">
              {docName}
            </span>
          </div>
          {isTextMode ? (
            <div className="max-h-[480px] overflow-y-auto px-6 py-6 text-[15px] leading-loose text-ink-700">
              <p className="whitespace-pre-wrap">{text}</p>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
              <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 text-[28px]">
                {isImage ? '📷' : '📄'}
              </span>
              <p className="mt-5 text-[16px] font-bold text-ink-900">{docName}</p>
              <p className="mt-2 max-w-sm text-[14px] leading-relaxed text-ink-400">
                {isImage
                  ? '사진 속 글자는 분석을 시작하면 OCR로 읽어요. 계약서 전체가 선명하게 나온 사진일수록 정확해요.'
                  : '텍스트 PDF는 그대로 읽고, 스캔본이면 자동으로 OCR로 전환돼요.'}
              </p>
            </div>
          )}
        </Card>

        {/* 사이드 정보 — 실제로 아는 것만 보여준다 */}
        <div className="flex flex-col gap-4">
          <Card className="px-5 py-5">
            <p className="text-[15px] font-bold text-ink-900">
              {isTextMode ? '입력 정보' : '파일 정보'}
            </p>
            <dl className="mt-4 space-y-3 text-[14px]">
              {isTextMode ? (
                <>
                  <InfoRow label="글자 수" value={`${charCount!.toLocaleString()}자`} />
                  <InfoRow
                    label="예상 조항 수"
                    value={clauseEstimate! > 0 ? `약 ${clauseEstimate}개` : '—'}
                  />
                </>
              ) : (
                <>
                  <InfoRow label="파일 형식" value={isImage ? '사진 (OCR)' : 'PDF'} />
                  {fileSizeMb && <InfoRow label="크기" value={`${fileSizeMb}MB`} />}
                </>
              )}
            </dl>
            <p className="mt-3.5 text-[12px] leading-relaxed text-ink-400">
              정확한 조항 수와 위험 여부는 분석을 시작하면 확인돼요.
            </p>
          </Card>

          {isTextMode && !enoughText ? (
            <div className="rounded-2xl bg-caution-50 px-4 py-3.5 text-[14px] font-semibold leading-relaxed text-caution-700">
              ⚠️ 내용이 너무 짧아요. 계약서 전체를 붙여넣으면 더 정확해요.
            </div>
          ) : (
            <div className="rounded-2xl bg-safe-50 px-4 py-3.5 text-[14px] font-semibold leading-relaxed text-safe-700">
              {isTextMode ? '✓ 분석하기에 충분한 텍스트가 확인됐어요' : '✓ 파일이 준비됐어요'}
            </div>
          )}

          <div className="mt-auto flex flex-col gap-2.5 pt-4">
            <Button size="lg" full onClick={onNext}>
              이 내용으로 계속
            </Button>
            <Button variant="secondary" full onClick={onPrev}>
              다시 올리기
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

function InfoRow({ label, value, good = false }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-ink-400">{label}</dt>
      <dd className={`font-bold ${good ? 'text-safe-700' : 'text-ink-900'}`}>{value}</dd>
    </div>
  )
}
