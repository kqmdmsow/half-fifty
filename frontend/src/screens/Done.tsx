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
    <>
    <PrintReport results={results} />
    <div className="mx-auto max-w-3xl animate-fade-up px-6 py-12 md:py-16 print:hidden">
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

      <div className="mt-10">
        <h2 className="text-[18px] font-bold tracking-[-0.01em] text-ink-900">
          바로 상담받을 수 있는 곳
        </h2>
        <p className="mt-1.5 text-[14px] text-ink-400">
          위에서 복사한 상담 요약을 들고 연락하면 이야기가 훨씬 빨라져요. 모두 공공기관의
          무료 상담이에요.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {buildConsultServices(results).map((service) => (
            <ConsultCard key={service.name} {...service} />
          ))}
        </div>
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
    </>
  )
}

/** 인쇄(PDF 저장) 전용 리포트 — 화면에는 숨겨지고 window.print() 시에만 렌더링.
 *  Done 화면 자체를 인쇄하면 분석 결과가 하나도 안 담기던 문제의 해결책. */
function PrintReport({ results }: { results: ClauseResult[] }) {
  const risky = results.filter((r) => r.risk_level !== '안전')
  return (
    <div className="hidden px-8 py-6 print:block">
      <h1 className="text-[20px] font-bold text-ink-900">하프피프티 계약서 분석 결과</h1>
      <p className="mt-1 text-[11px] text-ink-400">
        전체 {results.length}개 조항 중 확인이 필요한 조항 {risky.length}개 · 본 결과는 참고용
        안내이며 법률 자문이 아닙니다. 중요한 결정은 반드시 전문가와 상담하세요.
      </p>
      {results.map((r) => (
        <div
          key={r.clause_id}
          className="mt-4 border-t border-ink-100 pt-3"
          style={{ breakInside: 'avoid' }}
        >
          <p className="text-[13px] font-bold text-ink-900">
            [{r.risk_level}] {r.risk_type !== '해당 없음' ? r.risk_type : '표준 조항'}
          </p>
          <p className="mt-1 text-[11px] leading-relaxed text-ink-700">원문: {r.original_text}</p>
          <p className="mt-1 text-[11px] leading-relaxed text-ink-900">설명: {r.explanation}</p>
          {r.risk_level !== '안전' && r.risk_evidence && (
            <p className="mt-1 text-[11px] leading-relaxed text-ink-700">근거: {r.risk_evidence}</p>
          )}
          {r.check_questions.length > 0 && (
            <ul className="mt-1 list-disc pl-5 text-[11px] leading-relaxed text-ink-700">
              {r.check_questions.map((q) => (
                <li key={q}>확인할 것: {q}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  )
}

/** 분석 결과에서 계약 도메인을 추론해 변호사 검색 키워드로 쓴다.
 *  (도메인 라우팅 PR#24 머지 전까지의 프론트 단독 휴리스틱 — 머지 후 서버
 *  판정으로 대체 가능) */
function consultKeyword(results: ClauseResult[]): string {
  const text = results.map((r) => `${r.risk_type} ${r.original_text}`).join(' ')
  if (/보증금|임대차|임차|전세|월세|임대인/.test(text)) return '임대차'
  if (/대출|이자|금리|보험|카드|연금|투자|상환/.test(text)) return '금융'
  return '계약'
}

function buildConsultServices(results: ClauseResult[]) {
  const keyword = consultKeyword(results)
  return [
    {
      name: '대한법률구조공단',
      desc: '계약서·임대차 등 모든 법률 문제 무료 상담',
      phone: '132',
      url: 'https://www.klac.or.kr',
    },
    {
      name: '나의 변호사 (대한변호사협회)',
      desc: `이 계약과 맞는 '${keyword}' 분야 변호사를 바로 검색해 연결`,
      phone: null,
      url: `https://www.klaw.or.kr/search?keyword=${encodeURIComponent(keyword)}`,
    },
    {
      name: '전세피해지원센터',
      desc: '전세사기·보증금 피해 전문 상담 (국토교통부)',
      phone: '1533-8119',
      url: 'https://www.khug.or.kr/jeonse',
    },
    {
      name: '금융감독원 금융민원센터',
      desc: '대출·보험·금융상품 분쟁과 피해 상담',
      phone: '1332',
      url: 'https://www.fss.or.kr',
    },
  ]
}

function ConsultCard({
  name,
  desc,
  phone,
  url,
}: {
  name: string
  desc: string
  phone: string | null
  url: string
}) {
  return (
    <Card className="flex flex-col items-start p-5">
      <p className="text-[15px] font-bold text-ink-900">{name}</p>
      <p className="mb-3.5 mt-1 flex-1 text-[13px] leading-relaxed text-ink-400">{desc}</p>
      <div className="flex gap-2">
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg bg-brand-50 px-2.5 py-1.5 text-[13px] font-bold text-brand-600 hover:bg-brand-100"
        >
          홈페이지 열기
        </a>
        {phone && (
          <a
            href={`tel:${phone}`}
            className="rounded-lg bg-ink-50 px-2.5 py-1.5 text-[13px] font-bold text-ink-600 hover:bg-ink-100"
          >
            전화 {phone}
          </a>
        )}
      </div>
    </Card>
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
