import { useState } from 'react'
import type { ClauseResult } from '../api'
import { Button, Card, CopyButton } from '../components/ui'
import { riskLevelLabel, riskLevelLabel as rl, riskTypeLabel, t, type LangCode } from '../i18n'
import { clauseHeading } from '../clauseTitle'
import { FeedbackCard } from '../components/FeedbackCard'
import { deleteRecord } from '../records'


/** 점역기가 헷갈리는 기호를 평이한 문자로 바꾼다 (#126).
 *
 * 점자정보단말기는 텍스트를 자체 점역하는데, 장식 기호(■)나 전각 인용부호
 * (「」)는 점역기·규정판마다 처리가 갈려 정체불명 점형이나 잡음으로 읽힌다.
 * LLM이 근거에 쓰는 「」까지 걸러야 해서 출력 직전에 일괄 정리한다.
 */
function braillePlain(text: string): string {
  return text
    .replace(/[「」『』]/g, '"')
    .replace(/[—–]/g, '-')
    .replace(/[■◆●▶▲]/g, '')
    .replace(/·/g, ', ')
    .replace(/[ \t]{2,}/g, ' ')
    .trim()
}

/** 머리말 날짜 표기용 로케일 (i18n LangCode → BCP-47). */
const LOCALE: Record<string, string> = {
  ko: 'ko-KR', en: 'en-US', zh: 'zh-CN', vi: 'vi-VN', th: 'th-TH', id: 'id-ID',
  tl: 'fil-PH', ne: 'ne-NP', km: 'km-KH', my: 'my-MM', mn: 'mn-MN', uz: 'uz-UZ',
  si: 'si-LK', bn: 'bn-BD', ru: 'ru-RU', ja: 'ja-JP',
}

export function DoneScreen({
  results,
  language = 'ko',
  resultsShownAt = null,
  recordSaved = false,
  savedRecordId = null,
  onRestart,
}: {
  results: ClauseResult[]
  language?: LangCode
  resultsShownAt?: number | null
  /** 옵트인 로컬 기록(#102 v1)으로 이 결과를 저장했는지 — 삭제 안내 문구 분기용 */
  recordSaved?: boolean
  /** 저장된 기록의 id — '지금 삭제'를 누르면 이 기록도 함께 지운다(문구·실제
      동작 불일치 방지: "모든 데이터를 삭제했어요"인데 내 기록에 남아있으면 안 됨) */
  savedRecordId?: string | null
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
          {t(language, 'doDeletedTitle')}
        </h1>
        <p className="mt-2.5 text-[15px] leading-relaxed text-ink-400">
          {t(language, 'doDeletedDesc')}
        </p>
        <Button size="lg" className="mt-8" onClick={onRestart}>
          {t(language, 'doNew')}
        </Button>
      </div>
    )
  }

  return (
    <>
    <PrintReport results={results} language={language} />
    <div className="mx-auto max-w-3xl animate-fade-up px-6 py-12 md:py-16 print:hidden">
      <div className="text-center">
        <span className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-brand-50 text-[28px]">
          ✓
        </span>
        <h1 className="mt-5 text-[26px] font-bold tracking-[-0.02em] text-ink-900 md:text-[30px]">
          {t(language, 'doTitle')}
        </h1>
        <p className="mt-2.5 text-[15px] text-ink-400">
          {t(language, 'doSubtitle')}
        </p>
      </div>

      {/* 결과 텍스트 다운로드 (#126 v1) — 점자정보단말기·문서 앱은 txt를
          그대로 읽는다(단말기 자체 점역이 표준 사용). 자체 BRF 점역은
          한국 점자 규정 오변환 위험이 있어 후속(liblouis 검증 후). */}
      <div className="mx-auto mt-4 max-w-md text-center">
        <button
          type="button"
          onClick={() => {
            const lines: string[] = []
            // 머리말 — 점자단말기는 화면을 한눈에 훑을 수 없어 한 줄씩 읽는다.
            // 무엇을·언제·몇 건인지 맨 앞에서 알려줘야 방향을 잡을 수 있다.
            const counts = results.reduce(
              (acc, r) => ({ ...acc, [r.risk_level]: (acc[r.risk_level] ?? 0) + 1 }),
              {} as Record<string, number>,
            )
            lines.push(braillePlain(t(language, 'dlDocTitle')))
            lines.push(new Intl.DateTimeFormat(LOCALE[language] ?? 'ko-KR', {
              year: 'numeric', month: 'long', day: 'numeric',
            }).format(new Date()))
            lines.push(
              braillePlain(
                t(language, 'dlDocSummary', {
                  total: results.length,
                  danger: counts['위험'] ?? 0,
                  caution: counts['주의'] ?? 0,
                }),
              ),
            )
            lines.push('')
            results.forEach((r) => {
              const head = clauseHeading(r.original_text, language, r.original_text_translated) ?? r.clause_id
              lines.push(braillePlain(`[${t(language, 'dlClauseLabel')}] ${head} - ${rl(language, r.risk_level)}`))
              lines.push(braillePlain(r.explanation))
              if (r.risk_level !== '안전' && !r.analysis_failed) {
                lines.push(braillePlain(`[근거] ${r.risk_evidence_translated || r.risk_evidence}`))
              }
              r.check_questions.forEach((q, i) => lines.push(braillePlain(`[질문${i + 1}] ${q}`)))
              lines.push(braillePlain(`[원문] ${r.original_text}`))
              lines.push('')
            })
            const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/plain;charset=utf-8' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `${t(language, 'dlFilename')}.txt`
            a.click()
            URL.revokeObjectURL(url)
          }}
          className="rounded-xl bg-ink-50 px-4 py-2.5 text-[14px] font-bold text-ink-700 transition-colors hover:bg-ink-100"
        >
          {t(language, 'dlBtn')}
        </button>
        <p className="mt-1.5 text-[12px] text-ink-400">{t(language, 'dlNote')}</p>
      </div>

      {/* 사람 평가 수집 (자문 §6) — 만족도 + 읽기 시간, 로컬 익명 집계 */}
      <div className="mx-auto mt-8 max-w-md">
        <FeedbackCard resultsShownAt={resultsShownAt} language={language} />
      </div>

      <div className="mt-10 grid gap-4 md:grid-cols-3">
        <ActionCard
          title={t(language, 'doCard1T')}
          body={t(language, 'doCard1B')}
        >
          <CopyButton text={allQuestions || '-'} copiedText={t(language, 'doCopied')}>
            {t(language, 'doCopyQ')}
          </CopyButton>
        </ActionCard>
        <ActionCard title={t(language, 'doCard2T')} body={t(language, 'doCard2B')}>
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-lg bg-brand-50 px-2.5 py-1.5 text-[13px] font-bold text-brand-600 hover:bg-brand-100"
          >
            {t(language, 'doPrint')}
          </button>
        </ActionCard>
        <ActionCard
          title={t(language, 'doCard3T')}
          body={t(language, 'doCard3B')}
        >
          <CopyButton text={consultSummary || '-'} copiedText={t(language, 'doCopied')}>
            {t(language, 'doCopyC')}
          </CopyButton>
        </ActionCard>
      </div>

      <div className="mt-10">
        <h2 className="text-[18px] font-bold tracking-[-0.01em] text-ink-900">
          {t(language, 'doConsultTitle')}
        </h2>
        <p className="mt-1.5 text-[14px] text-ink-400">
          {t(language, 'doConsultDesc')}
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {buildConsultServices(results, language).map((service) => (
            <ConsultCard key={service.name} {...service} language={language} />
          ))}
        </div>
      </div>

      <Card className="mt-8 flex flex-col items-start justify-between gap-4 p-6 md:flex-row md:items-center">
        <div>
          {/* 옵트인 로컬 기록(#102 v1)으로 저장한 경우 "화면을 닫으면 사라져요"가
              더 이상 사실이 아니므로 문구를 분기한다 — 모호한 절충 문구 대신
              두 상황 각각 정확한 문구를 쓴다(프라이버시 문구는 모호하면 불신). */}
          <p className="text-[15px] font-bold text-ink-900">
            {t(language, recordSaved ? 'doDeleteTitleSaved' : 'doDeleteTitle')}
          </p>
          <p className="mt-1 text-[14px] leading-relaxed text-ink-400">
            {t(language, recordSaved ? 'doDeleteDescSaved' : 'doDeleteDesc')}
          </p>
        </div>
        {confirming ? (
          <div className="flex shrink-0 gap-2">
            <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
              {t(language, 'doCancel')}
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => {
                if (savedRecordId) deleteRecord(savedRecordId)
                setDeleted(true)
              }}
            >
              {t(language, 'doConfirmDel')}
            </Button>
          </div>
        ) : (
          <Button variant="danger" size="sm" onClick={() => setConfirming(true)}>
            {t(language, 'doDeleteBtn')}
          </Button>
        )}
      </Card>

      <div className="mt-9 text-center">
        <Button variant="secondary" onClick={onRestart}>
          {t(language, 'doNew')}
        </Button>
      </div>
    </div>
    </>
  )
}

/** 인쇄(PDF 저장) 전용 리포트 — 화면에는 숨겨지고 window.print() 시에만 렌더링.
 *  Done 화면 자체를 인쇄하면 분석 결과가 하나도 안 담기던 문제의 해결책. */
function PrintReport({ results, language = 'ko' }: { results: ClauseResult[]; language?: LangCode }) {
  const risky = results.filter((r) => r.risk_level !== '안전')
  return (
    <div className="hidden px-8 py-6 print:block">
      <h1 className="text-[20px] font-bold text-ink-900">{t(language, 'prTitle')}</h1>
      <p className="mt-1 text-[11px] text-ink-400">
        {t(language, 'prSummary', { total: results.length, need: risky.length })}
      </p>
      {results.map((r) => (
        <div
          key={r.clause_id}
          className="mt-4 border-t border-ink-100 pt-3"
          style={{ breakInside: 'avoid' }}
        >
          <p className="text-[13px] font-bold text-ink-900">
            [{riskLevelLabel(language, r.risk_level)}]{' '}
            {r.risk_type !== '해당 없음' ? riskTypeLabel(language, r.risk_type) : t(language, 'standardClause')}
          </p>
          <p className="mt-1 text-[11px] leading-relaxed text-ink-700">{t(language, 'prOriginal')}: {r.original_text}</p>
          <p className="mt-1 text-[11px] leading-relaxed text-ink-900">{t(language, 'prExplain')}: {r.explanation}</p>
          {r.risk_level !== '안전' && r.risk_evidence && (
            <p className="mt-1 text-[11px] leading-relaxed text-ink-700">{t(language, 'evidence')}: {r.risk_evidence}</p>
          )}
          {r.check_questions.length > 0 && (
            <ul className="mt-1 list-disc pl-5 text-[11px] leading-relaxed text-ink-700">
              {r.check_questions.map((q) => (
                <li key={q}>{t(language, 'prCheck')}: {q}</li>
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

function buildConsultServices(results: ClauseResult[], language: LangCode = 'ko') {
  const keyword = consultKeyword(results)
  return [
    {
      name: '대한법률구조공단',
      desc: t(language, 'doSvcKlac'),
      phone: '132',
      url: 'https://www.klac.or.kr',
    },
    {
      name: '나의 변호사 (대한변호사협회)',
      // klaw는 검색 상태를 URL에 싣지 않는 SPA라 딥링크 필터가 불가능 —
      // 검색어를 자동 복사해주고 붙여넣도록 안내한다 (협회 API 제휴 전 차선책).
      desc: t(language, 'doSvcKlaw', { keyword }),
      phone: null,
      url: 'https://www.klaw.or.kr/search',
      copyKeyword: keyword,
    },
    {
      name: '전세피해지원센터',
      desc: t(language, 'doSvcJeonse'),
      phone: '1533-8119',
      url: 'https://www.khug.or.kr/jeonse',
    },
    {
      name: '금융감독원 금융민원센터',
      desc: t(language, 'doSvcFss'),
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
  copyKeyword,
  language = 'ko',
}: {
  name: string
  desc: string
  phone: string | null
  url: string
  copyKeyword?: string
  language?: LangCode
}) {
  const openWithKeyword = () => {
    if (copyKeyword) {
      navigator.clipboard?.writeText(copyKeyword).catch(() => {})
    }
    window.open(url, '_blank', 'noopener,noreferrer')
  }
  return (
    <Card className="flex flex-col items-start p-5">
      <p className="text-[15px] font-bold text-ink-900">{name}</p>
      <p className="mb-3.5 mt-1 flex-1 text-[13px] leading-relaxed text-ink-400">{desc}</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={openWithKeyword}
          className="rounded-lg bg-brand-50 px-2.5 py-1.5 text-[13px] font-bold text-brand-600 hover:bg-brand-100"
        >
          {copyKeyword ? t(language, 'doCopyOpen', { keyword: copyKeyword }) : t(language, 'doOpen')}
        </button>
        {phone && (
          <a
            href={`tel:${phone}`}
            className="rounded-lg bg-ink-50 px-2.5 py-1.5 text-[13px] font-bold text-ink-600 hover:bg-ink-100"
          >
            {t(language, 'doCall')} {phone}
          </a>
        )}
      </div>
    </Card>
  )
}

function ActionCard({
  title,
  body,
  children,
}: {
  title: string
  body: string
  children: React.ReactNode
}) {
  return (
    <Card className="flex flex-col items-start p-6">
      <p className="mt-3.5 text-[16px] font-bold text-ink-900">{title}</p>
      <p className="mb-4 mt-1.5 flex-1 text-[13px] leading-relaxed text-ink-400">{body}</p>
      {children}
    </Card>
  )
}
