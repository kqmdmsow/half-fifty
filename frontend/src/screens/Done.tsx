import { useState } from 'react'
import type { ClauseResult } from '../api'
import { Button, Card, CopyButton } from '../components/ui'

export function DoneScreen({
  results,
  onRestart,
}: {
  results: ClauseResult[]
  onRestart: () => void
}) {
  const [deleted, setDeleted] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const allQuestions = results
    .flatMap((result) => result.check_questions)
    .map((question, index) => `${index + 1}. ${question}`)
    .join('\n')

  const consultSummary = results
    .filter((result) => result.risk_level !== '안전')
    .map(
      (result) =>
        `[${result.risk_level}] ${result.risk_type}\n원문: ${result.original_text}\n설명: ${result.explanation}`,
    )
    .join('\n\n')

  if (deleted) {
    return (
      <div className="mx-auto flex min-h-[70vh] max-w-md flex-col items-center justify-center px-6 text-center">
        <span className="flex h-16 w-16 items-center justify-center rounded-full bg-safe-50 text-[28px]">
          ✓
        </span>
        <h1 className="mt-6 text-[24px] font-bold tracking-[-0.02em] text-ink-900">
          모든 데이터를 삭제했어요
        </h1>
        <p className="mt-2.5 text-[15px] leading-relaxed text-ink-400">
          계약서 원본과 분석 결과가 모두 지워졌어요.
          <br />
          필요할 때 언제든 다시 이용하세요.
        </p>
        <Button size="lg" className="mt-8" onClick={onRestart}>
          새 계약서 분석하기
        </Button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl animate-fade-up px-6 py-12 md:py-16">
      <div className="text-center">
        <span className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-brand-50 text-[28px]">
          🎉
        </span>
        <h1 className="mt-5 text-[26px] font-bold tracking-[-0.02em] text-ink-900 md:text-[30px]">
          분석이 끝났어요. 이제 이렇게 해보세요
        </h1>
        <p className="mt-2.5 text-[15px] text-ink-400">
          질문을 준비하고, 중요한 조항은 전문가와 상담하세요.
        </p>
      </div>

      <div className="mt-10 grid gap-4 md:grid-cols-3">
        <ActionCard
          emoji="💬"
          title="확인 질문 준비"
          body="상대방에게 물어볼 질문을 한 번에 복사해요."
        >
          <CopyButton text={allQuestions || '확인할 질문이 없어요.'} copiedText="복사 완료!">
            질문 목록 복사
          </CopyButton>
        </ActionCard>
        <ActionCard emoji="🖨️" title="결과 저장" body="위험 조항과 근거를 문서로 남겨요.">
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-lg bg-brand-50 px-2.5 py-1.5 text-[13px] font-bold text-brand-600 hover:bg-brand-100"
          >
            인쇄 · PDF 저장
          </button>
        </ActionCard>
        <ActionCard
          emoji="👩‍⚖️"
          title="전문가 상담 준비"
          body="중요 조항을 원문과 함께 정리해요."
        >
          <CopyButton text={consultSummary || '위험 조항이 없어요.'} copiedText="복사 완료!">
            상담 요약 복사
          </CopyButton>
        </ActionCard>
      </div>

      <Card className="mt-8 flex flex-col items-start justify-between gap-4 p-6 md:flex-row md:items-center">
        <div>
          <p className="text-[15px] font-bold text-ink-900">결과는 24시간 뒤 자동 삭제돼요</p>
          <p className="mt-1 text-[14px] leading-relaxed text-ink-400">
            지금 바로 삭제할 수도 있어요. 삭제하면 결과를 다시 볼 수 없어요.
          </p>
        </div>
        {confirming ? (
          <div className="flex shrink-0 gap-2">
            <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
              취소
            </Button>
            <Button variant="danger" size="sm" onClick={() => setDeleted(true)}>
              정말 삭제하기
            </Button>
          </div>
        ) : (
          <Button variant="danger" size="sm" onClick={() => setConfirming(true)}>
            지금 모두 삭제
          </Button>
        )}
      </Card>

      <div className="mt-9 text-center">
        <Button variant="secondary" onClick={onRestart}>
          새 계약서 분석하기
        </Button>
      </div>
    </div>
  )
}

function ActionCard({
  emoji,
  title,
  body,
  children,
}: {
  emoji: string
  title: string
  body: string
  children: React.ReactNode
}) {
  return (
    <Card className="flex flex-col items-start p-6">
      <span className="text-[26px]">{emoji}</span>
      <p className="mt-3.5 text-[16px] font-bold text-ink-900">{title}</p>
      <p className="mb-4 mt-1.5 flex-1 text-[13px] leading-relaxed text-ink-400">{body}</p>
      {children}
    </Card>
  )
}
