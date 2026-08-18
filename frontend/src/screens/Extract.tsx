import { Button, Card, PageTitle } from '../components/ui'
import { t, type LangCode } from '../i18n'

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
  language = 'ko',
  onPrev,
  onNext,
}: {
  file: File | null
  mode: 'pdf' | 'text'
  text: string
  language?: LangCode
  onPrev: () => void
  onNext: () => void
}) {
  const isTextMode = mode === 'text' && text.trim().length > 0
  const docName = file?.name ?? (isTextMode ? t(language, 'exCardText') : t(language, 'exCardFile'))

  const clauseEstimate = isTextMode ? estimateClauseCount(text) : null
  const charCount = isTextMode ? text.trim().length : null
  const enoughText = isTextMode ? text.trim().length >= MIN_TEXT_LENGTH : true

  const isImage = file?.type.startsWith('image/') ?? false
  const fileSizeMb = file ? (file.size / 1024 / 1024).toFixed(1) : null

  return (
    <div className="mx-auto max-w-5xl animate-fade-up px-6 py-12 md:py-16">
      <PageTitle
        title={isTextMode ? t(language, 'exTitleText') : t(language, 'exTitleFile')}
        desc={isTextMode ? t(language, 'exDescText') : t(language, 'exDescFile')}
      />

      <div className="mt-8 grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
        {/* 본문: 텍스트 모드는 실제 입력 내용, 파일 모드는 파일 안내 */}
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-ink-50 px-6 py-4">
            <p className="text-[15px] font-bold text-ink-900">
              {isTextMode ? t(language, 'exCardText') : t(language, 'exCardFile')}
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
                {isImage ? t(language, 'exOcrImage') : t(language, 'exOcrPdf')}
              </p>
            </div>
          )}
        </Card>

        {/* 사이드 정보 — 실제로 아는 것만 보여준다 */}
        <div className="flex flex-col gap-4">
          <Card className="px-5 py-5">
            <p className="text-[15px] font-bold text-ink-900">
              {isTextMode ? t(language, 'exInfoText') : t(language, 'exInfoFile')}
            </p>
            <dl className="mt-4 space-y-3 text-[14px]">
              {isTextMode ? (
                <>
                  <InfoRow label={t(language, 'exChars')} value={charCount!.toLocaleString()} />
                  <InfoRow
                    label={t(language, 'exClauses')}
                    value={clauseEstimate! > 0 ? t(language, 'exAbout', { n: clauseEstimate! }) : '—'}
                  />
                </>
              ) : (
                <>
                  <InfoRow label={t(language, 'exFileType')} value={isImage ? t(language, 'exPhotoOcr') : 'PDF'} />
                  {fileSizeMb && <InfoRow label={t(language, 'exSize')} value={`${fileSizeMb}MB`} />}
                </>
              )}
            </dl>
            <p className="mt-3.5 text-[12px] leading-relaxed text-ink-400">
              {t(language, 'exNote')}
            </p>
          </Card>

          {isTextMode && !enoughText ? (
            <div className="rounded-2xl bg-caution-50 px-4 py-3.5 text-[14px] font-semibold leading-relaxed text-caution-700">
              ⚠️ {t(language, 'exShort')}
            </div>
          ) : (
            <div className="rounded-2xl bg-safe-50 px-4 py-3.5 text-[14px] font-semibold leading-relaxed text-safe-700">
              ✓ {isTextMode ? t(language, 'exEnough') : t(language, 'exFileReady')}
            </div>
          )}

          <div className="mt-auto flex flex-col gap-2.5 pt-4">
            <Button size="lg" full onClick={onNext}>
              {t(language, 'exContinue')}
            </Button>
            <Button variant="secondary" full onClick={onPrev}>
              {t(language, 'exReupload')}
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
