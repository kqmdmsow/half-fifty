import { Button, Card, PageTitle } from '../components/ui'

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
  const docName = file?.name ?? (mode === 'text' ? '직접 입력한 내용' : '계약서.pdf')

  return (
    <div className="mx-auto max-w-5xl animate-fade-up px-6 py-12 md:py-16">
      <PageTitle
        title="내용이 제대로 읽혔는지 확인해 주세요"
        desc="내용이 깨졌거나 빠졌다면 다시 올려주세요. 스캔본은 아직 지원하지 않아요."
      />

      <div className="mt-8 grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
        {/* 추출 본문 */}
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-ink-50 px-6 py-4">
            <p className="text-[15px] font-bold text-ink-900">추출된 내용</p>
            <span className="max-w-52 truncate rounded-lg bg-ink-50 px-3 py-1 text-[13px] font-semibold text-ink-600">
              {docName}
            </span>
          </div>
          <div className="max-h-[480px] overflow-y-auto px-6 py-6 text-[15px] leading-loose text-ink-700">
            {mode === 'text' && text.trim() ? (
              <p className="whitespace-pre-wrap">{text}</p>
            ) : (
              <>
                <p className="text-center font-bold text-ink-900">주택임대차 계약서</p>
                <p className="mt-5 font-bold text-ink-900">제1조(목적)</p>
                <p>
                  임대인과 임차인은 아래 표시 주택에 관하여 다음 계약 내용과 같이 임대차계약을
                  체결한다.
                </p>
                <p className="mt-4 font-bold text-ink-900">제2조(보증금의 반환)</p>
                <p>임대인은 계약 종료 후 3개월 이내에 임차인에게 보증금을 반환할 수 있다.</p>
                <p className="mt-4 font-bold text-ink-900">제3조(계약의 해지)</p>
                <p>임차인이 차임을 2기 이상 연체한 경우 임대인은 계약을 해지할 수 있다.</p>
              </>
            )}
          </div>
        </Card>

        {/* 사이드 정보 */}
        <div className="flex flex-col gap-4">
          <Card className="px-5 py-5">
            <p className="text-[15px] font-bold text-ink-900">문서 정보</p>
            <dl className="mt-4 space-y-3 text-[14px]">
              <InfoRow label="예상 문서 종류" value="주택임대차 계약서" />
              <InfoRow label="감지된 조항" value="16개" />
              <InfoRow label="텍스트 인식률" value="높음" good />
            </dl>
          </Card>

          <div className="rounded-2xl bg-safe-50 px-4 py-3.5 text-[14px] font-semibold leading-relaxed text-safe-700">
            ✓ 분석하기에 충분한 텍스트가 확인됐어요
          </div>

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
