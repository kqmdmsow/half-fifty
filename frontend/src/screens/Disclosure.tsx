/**
 * 설명·서명 대조 검증 화면 (#175, 2순위).
 *
 * 계약서만 보면 "무엇에 서명했는가"는 알 수 있지만 "무엇을 설명받았는가"는
 * 알 수 없다. 불완전판매는 대부분 서류가 아니라 상담 현장에서 생긴다.
 *
 * 화면 설계에서 지킨 것:
 * - **지적마다 양쪽 원문을 나란히 보여 준다.** 계약서 인용과 발화 인용을 각각
 *   하이라이트해서, 사용자가 "AI가 그렇다니까"가 아니라 직접 대조해 납득하게 한다.
 * - **"지적 없음"과 "검증 실패"를 구분한다.** 둘을 같은 화면으로 보여 주면
 *   실패가 "문제 없음"으로 읽혀 정반대 결론을 준다.
 * - **한계를 결과 아래에 붙인다.** 법적 판단이 아니고 제출한 자료 안에서만
 *   비교한 것이라는 사실을 결과와 같은 화면에 둔다.
 */
import { useState } from 'react'

import { verifyDisclosure, verifyDisclosureAudio,
         type DisclosureFinding, type DisclosureResponse,
         type Language, type Persona } from '../api'
import { Button, Card, PageTitle } from '../components/ui'
import { HighlightedText } from '../components/HighlightedText'
import { t, type LangCode } from '../i18n'

const SEVERITY_STYLE: Record<string, string> = {
  높음: 'bg-danger-50 text-danger-600 border-danger-500',
  보통: 'bg-caution-50 text-caution-600 border-caution-500',
  낮음: 'bg-ink-100 text-ink-600 border-ink-200',
}

const SAMPLE_CONTRACT = [
  '제1조(대출조건) 대출금액은 금 20,000,000원, 대출기간은 계약일로부터 36개월로 한다.',
  '제2조(이자) 이자율은 갑의 내부 사정에 따라 수시로 변경될 수 있다. 변경된 이자율은 갑의 홈페이지 공지로 갈음한다.',
  '제3조(기한의 이익 상실) 을이 이자 지급을 1회라도 지체한 경우 갑은 즉시 대출금 전액의 상환을 청구할 수 있다.',
  '제4조(중도상환수수료) 중도상환수수료는 상환원금의 1.5%로 하며, 대출일로부터 3년 경과 시 면제한다.',
].join('\n')

const SAMPLE_TRANSCRIPT = [
  '[상담사] 어르신 안녕하세요. 오늘 대출 상담 도와드리겠습니다.',
  '[고객] 네, 이천만원 필요해서요.',
  '[상담사] 네, 이천만원에 36개월로 진행하시면 되고요. 금리는 지금 기준으로 연 4.5% 나옵니다.',
  '[고객] 이자가 나중에 오르거나 하진 않나요?',
  '[상담사] 걱정 안 하셔도 됩니다. 저희가 다 알아서 해드려요. 손해 볼 일 없습니다.',
  '[고객] 아 네...',
  '[상담사] 그럼 여기 서명만 해주시면 됩니다.',
  '[고객] 이거 다 읽어봐야 하나요?',
  '[상담사] 아니요 그냥 형식적인 거예요. 서명만 하시면 돼요.',
].join('\n')

function FindingCard({
  finding, language, clauseText,
}: {
  finding: DisclosureFinding
  language: LangCode
  /** 계약서 조항 전문. 있으면 근거를 그 안에서 하이라이트하고, 없으면 인용만 낸다. */
  clauseText: string
}) {
  const label = t(language, `ft${finding.finding_type}` as 'ft미고지_비용')
  return (
    <Card className="mt-3">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[15px] font-bold text-ink-900">{label}</p>
        <span
          className={`shrink-0 rounded-lg border px-2 py-0.5 text-[12px] font-bold ${
            SEVERITY_STYLE[finding.severity] ?? SEVERITY_STYLE.보통
          }`}
        >
          {finding.severity}
        </span>
      </div>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-600">{finding.explanation}</p>

      {/* 양쪽 원문을 나란히 — 사용자가 직접 대조해 납득하게 한다 */}
      {finding.clause_quote && (
        <div className="mt-3 rounded-xl bg-ink-25 px-4 py-3">
          <p className="text-[12px] font-bold text-ink-400">{t(language, 'dvContractSide')}</p>
          <p className="mt-1 text-[14px] leading-relaxed text-ink-700">
            <HighlightedText text={clauseText || finding.clause_quote}
                             spans={clauseText ? finding.clause_spans : []} />
          </p>
        </div>
      )}
      <div className="mt-2 rounded-xl bg-ink-25 px-4 py-3">
        <p className="text-[12px] font-bold text-ink-400">{t(language, 'dvSpeechSide')}</p>
        {finding.speech_quote ? (
          <p className="mt-1 text-[14px] leading-relaxed text-ink-700">
            「<HighlightedText text={finding.speech_quote} />」
          </p>
        ) : (
          <p className="mt-1 text-[14px] font-semibold leading-relaxed text-danger-600">
            {t(language, 'dvNotSaid')}
          </p>
        )}
      </div>
    </Card>
  )
}

export function DisclosureScreen({
  language, persona, onBack,
}: {
  language: LangCode
  persona: Persona
  onBack: () => void
}) {
  const [contract, setContract] = useState('')
  const [transcript, setTranscript] = useState('')
  const [audio, setAudio] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DisclosureResponse | null>(null)

  const canRun = contract.trim().length > 20 && (audio !== null || transcript.trim().length > 20)

  async function run() {
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const res = audio
        ? await verifyDisclosureAudio(
            new File([contract], 'contract.txt', { type: 'text/plain' }),
            audio, persona, language as Language)
        : await verifyDisclosure(contract, transcript, persona, language as Language)
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const clauseTextById = new Map(
    (result?.results ?? []).map((r) => [r.clause_id, r.original_text]))

  return (
    <div className="mx-auto max-w-3xl px-4 pb-16">
      <PageTitle title={t(language, 'dvTitle')} desc={t(language, 'dvDesc')} />
      <p className="mt-3 rounded-xl bg-ink-25 px-4 py-3 text-[14px] leading-relaxed text-ink-500">
        {t(language, 'dvWhy')}
      </p>

      {!result && (
        <>
          <label className="mt-6 block text-[14px] font-bold text-ink-900">
            {t(language, 'dvContract')}
          </label>
          <textarea
            value={contract}
            onChange={(e) => setContract(e.target.value)}
            placeholder={t(language, 'dvContractPh')}
            rows={7}
            className="mt-2 w-full rounded-xl border border-ink-200 p-3 text-[14px] leading-relaxed"
          />

          <label className="mt-5 block text-[14px] font-bold text-ink-900">
            {t(language, 'dvTranscript')}
          </label>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder={t(language, 'dvTranscriptPh')}
            rows={7}
            disabled={audio !== null}
            className="mt-2 w-full rounded-xl border border-ink-200 p-3 text-[14px] leading-relaxed disabled:bg-ink-25"
          />

          <div className="mt-3 rounded-xl border border-dashed border-ink-200 px-4 py-3">
            <label className="text-[14px] font-bold text-ink-900">{t(language, 'dvAudio')}</label>
            <p className="mt-1 text-[13px] text-ink-400">{t(language, 'dvAudioHint')}</p>
            <input
              type="file"
              accept="audio/*"
              onChange={(e) => setAudio(e.target.files?.[0] ?? null)}
              className="mt-2 text-[13px]"
            />
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <Button onClick={run} disabled={!canRun || busy}>
              {busy ? t(language, 'dvRunning') : t(language, 'dvRun')}
            </Button>
            <Button
              variant="ghost"
              onClick={() => { setContract(SAMPLE_CONTRACT); setTranscript(SAMPLE_TRANSCRIPT); setAudio(null) }}
              disabled={busy}
            >
              {t(language, 'dvSample')}
            </Button>
            <Button variant="ghost" onClick={onBack} disabled={busy}>
              {t(language, 'dvBack')}
            </Button>
          </div>
        </>
      )}

      {/* 검증 실패는 '지적 없음'과 절대 같은 화면으로 보이면 안 된다 */}
      {error && (
        <p className="mt-5 rounded-xl border border-danger-500 bg-danger-50 px-4 py-3 text-[14px] font-semibold leading-relaxed text-danger-600">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-6">
          {result.warnings.map((w, i) => (
            <p key={i} className="mb-2 rounded-xl bg-caution-50 px-4 py-3 text-[13px] leading-relaxed text-ink-700">
              {w}
            </p>
          ))}

          <p className="text-[13px] text-ink-400">
            {t(language, 'dvChecked', { n: result.checked_clauses })}
          </p>

          {result.findings.length === 0 ? (
            <Card className="mt-3">
              <p className="text-[15px] font-bold text-ink-900">{t(language, 'dvNoFindings')}</p>
              <p className="mt-2 text-[14px] leading-relaxed text-ink-600">
                {t(language, 'dvNoFindingsDesc')}
              </p>
            </Card>
          ) : (
            <>
              <p className="mt-1 text-[17px] font-bold text-ink-900">
                {t(language, 'dvFound', { n: result.findings.length })}
              </p>
              {result.findings.map((f, i) => (
                <FindingCard
                  key={i} finding={f} language={language}
                  clauseText={clauseTextById.get(f.clause_id ?? '') ?? ''}
                />
              ))}
            </>
          )}

          <details className="mt-5 rounded-xl bg-ink-25 px-4 py-3">
            <summary className="cursor-pointer text-[14px] font-bold text-ink-700">
              {t(language, 'dvTranscriptTitle')}
            </summary>
            <p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-ink-600">
              {/* speech_spans는 발화 전문 기준 좌표다(api.ts DisclosureFinding) — 인용문이 아니라 여기서 하이라이트한다 */}
              <HighlightedText text={result.transcript}
                               spans={result.findings.flatMap((f) => f.speech_spans)} />
            </p>
          </details>

          <p className="mt-4 text-[13px] leading-relaxed text-ink-400">{t(language, 'dvLimit')}</p>

          <div className="mt-5">
            <Button variant="ghost" onClick={() => { setResult(null); setError(null) }}>
              {t(language, 'dvBack')}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
