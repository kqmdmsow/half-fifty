import { useEffect, useRef, useState } from 'react'
import { reexplainClause } from '../api'
import type { ClauseResult, Persona } from '../api'
import { Button, CopyButton, FirewallChip, RiskBadge, RiskIcon, WithheldBadge } from '../components/ui'
import { HighlightedText } from '../components/HighlightedText'
import { RISK_META } from '../data/sample'
import { riskLevelLabel, riskTypeLabel, t, type LangCode } from '../i18n'
import { clauseHeading } from '../clauseTitle'
import { FormattedText } from '../components/FormattedText'
import { isVoiceSupported, startVoiceSession, type VoiceSession } from '../voiceCommands'
import { speak, stopSpeaking, useVoiceAvailable, voiceAvailable } from '../tts'
import { agenciesForDomain, buildNegotiation } from '../data/actionGuide'

export function DetailScreen({
  clauseId,
  results,
  voiceGuide,
  language = 'ko',
  persona = 'adult',
  domain = '',
  onSelectClause,
  onBack,
  onDone,
}: {
  clauseId: string
  results: ClauseResult[]
  voiceGuide: boolean
  language?: LangCode
  persona?: Persona
  /** 문서 도메인 (Upload 사용자 선택, '' = 모름) — 구제기관 매칭용 */
  domain?: string
  onSelectClause: (clauseId: string) => void
  onBack: () => void
  onDone: () => void
}) {
  const clause = results.find((result) => result.clause_id === clauseId) ?? results[0]

  // 사용자 트리거 재설명 (#76) — judge 게이트 통과분만 반영, 조항당 2회 제한.
  // 판정 불변: explanation 표시만 오버라이드, risk_* 필드는 원본 그대로.
  const [reexplained, setReexplained] = useState<Record<string, { text: string; scores: Record<string, number> }>>({})
  const [reCount, setReCount] = useState<Record<string, number>>({})
  const [reState, setReState] = useState<'idle' | 'loading' | 'failed'>('idle')

  const requestReexplain = async (mode: 'easier' | 'detailed') => {
    if (!clause || reState === 'loading') return
    setReState('loading')
    try {
      const out = await reexplainClause(clause, mode, persona, language)
      setReCount((prev) => ({ ...prev, [clause.clause_id]: (prev[clause.clause_id] ?? 0) + 1 }))
      if (out.ok && out.explanation) {
        setReexplained((prev) => ({
          ...prev,
          [clause.clause_id]: { text: out.explanation!, scores: out.judge_scores ?? {} },
        }))
        setReState('idle')
      } else {
        setReState('failed')
      }
    } catch {
      setReState('failed')
    }
  }
  const [listening, setListening] = useState(false)
  const voiceReady = useVoiceAvailable(language)

  // 음성 안내: 화면 진입 시 설명 읽기 (기기 최적 한국어 보이스 자동 선택 — src/tts.ts)
  useEffect(() => {
    if (!voiceGuide || !clause || !voiceAvailable(language)) return
    speak(clause.explanation, language)
    return () => stopSpeaking()
  }, [voiceGuide, clause, language])

  // 수동 "들어보기" 버튼 상태(#118) — 조항을 바꾸면 이전 조항 재생 상태를 들고
  // 있지 않도록 초기화. 실제 정지는 위 effect의 cleanup(stopSpeaking)이 처리.
  useEffect(() => {
    setListening(false)
  }, [clause?.clause_id])

  // 음성 명령 (#127) — Detail 문맥에서 6종: 다음/이전/읽어줘/멈춰/요약/더 쉽게.
  // 인식 결과는 명령 해석 후 즉시 폐기 (전송·저장 없음).
  const [micOn, setMicOn] = useState(false)
  const voiceRef = useRef<VoiceSession | null>(null)
  const stateRef = useRef({ clauseId: '', results: [] as ClauseResult[] })
  stateRef.current = { clauseId: clause?.clause_id ?? '', results }
  // 음성 콜백은 마이크 켠 시점의 클로저를 계속 쓰므로, 최신 requestReexplain을 ref로 전달
  const reexplainRef = useRef(requestReexplain)
  reexplainRef.current = requestReexplain

  const toggleVoice = () => {
    if (voiceRef.current) {
      voiceRef.current.stop()
      voiceRef.current = null
      return
    }
    voiceRef.current = startVoiceSession((cmd) => {
      const { clauseId: cur, results: rs } = stateRef.current
      const idx = rs.findIndex((r) => r.clause_id === cur)
      const current = rs[idx]
      if (cmd === 'next' && idx < rs.length - 1) onSelectClause(rs[idx + 1].clause_id)
      else if (cmd === 'prev' && idx > 0) onSelectClause(rs[idx - 1].clause_id)
      else if (cmd === 'read' && current) speak(current.explanation, language)
      else if (cmd === 'stop') stopSpeaking()
      else if (cmd === 'summary') onBack()
      else if (cmd === 'easier') reexplainRef.current('easier')
    }, setMicOn)
  }

  useEffect(() => () => voiceRef.current?.stop(), [])

  // 결과가 아직 없으면 렌더링하지 않는다 (가짜 예시 폴백 제거 후의 방어선).
  // 훅 규칙 때문에 useEffect 뒤에 위치해야 한다.
  if (!clause) return null

  const questions = clause.check_questions.length
    ? clause.check_questions
    : [t(language, 'fallbackQuestion')]

  // 다음 행동 (과제 B) — 위험·주의이면서 판정이 유효한 조항에서만.
  // 판정 거부·분석 실패 조항에 요구 문구를 만들면 근거 없는 요구가 된다.
  const showNextActions =
    clause.risk_level !== '안전' && !clause.verdict_withheld && !clause.analysis_failed
  const negotiation = showNextActions ? buildNegotiation(clause) : ''

  return (
    <div className="mx-auto max-w-5xl animate-fade-up px-6 py-10 md:py-14">
      <button
        type="button"
        onClick={onBack}
        className="mb-6 inline-flex items-center gap-1.5 text-[14px] font-semibold text-ink-400 transition-colors hover:text-ink-900"
      >
        ← {t(language, 'backToSummary')}
      </button>

      {isVoiceSupported() && (
        <span className="mb-6 ml-3 inline-flex items-center gap-2">
          <button
            type="button"
            aria-pressed={micOn}
            onClick={toggleVoice}
            className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-[13px] font-bold transition-colors ${
              micOn ? 'bg-danger-500 text-white' : 'bg-ink-50 text-ink-600 hover:bg-ink-100'
            }`}
          >
            <span aria-hidden>🎤</span>
            {micOn ? t(language, 'vcOff') : t(language, 'vcToggle')}
          </button>
          {micOn && (
            <span className="text-[12px] font-semibold text-ink-400" role="status">
              {t(language, 'vcListening')}
            </span>
          )}
        </span>
      )}

      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        {/* 조항 목록 */}
        <aside className="lg:border-r lg:border-ink-50 lg:pr-6">
          <p className="px-1 text-[13px] font-bold text-ink-400">{t(language, 'clauseList')}</p>
          <nav className="mt-3 flex gap-2 overflow-x-auto pb-2 lg:flex-col lg:overflow-visible lg:pb-0">
            {results.map((result) => {
              const active = result.clause_id === clause.clause_id
              return (
                <button
                  key={result.clause_id}
                  type="button"
                  onClick={() => onSelectClause(result.clause_id)}
                  aria-label={`${clauseHeading(result.original_text, language, result.original_text_translated) ?? result.clause_id}, ${riskLevelLabel(language, result.risk_level)}`}
                  className={`flex shrink-0 items-center gap-2.5 rounded-2xl px-4 py-3 text-left text-[14px] font-semibold transition-colors ${
                    active
                      ? 'bg-ink-900 text-white'
                      : 'bg-ink-25 text-ink-600 hover:bg-ink-50'
                  }`}
                >
                  {/* 3중 인코딩: 색 점만으로 위험도를 표시하지 않는다 —
                      활성(어두운 배경) 칩에서는 현재색 상속으로 대비 유지 */}
                  <RiskIcon
                    level={result.risk_level}
                    className={active ? '' : RISK_META[result.risk_level].text}
                  />
                  <span className="whitespace-nowrap lg:whitespace-normal">
                    {clauseHeading(result.original_text, language, result.original_text_translated) ??
                      (result.risk_type === '해당 없음'
                        ? t(language, 'standardClause')
                        : riskTypeLabel(language, result.risk_type))}
                  </span>
                </button>
              )
            })}
          </nav>
        </aside>

        {/* 상세 */}
        <article>
          <div className="flex items-start justify-between gap-4">
            <div>
              {clause.verdict_withheld ? (
                <WithheldBadge label={t(language, 'fwWithheld')} />
              ) : (
                <RiskBadge level={clause.risk_level} label={riskLevelLabel(language, clause.risk_level)} />
              )}
              {!!clause.quarantined && (
                <FirewallChip label={t(language, 'fwQuarantined', { n: clause.quarantined })} />
              )}
              {clause.injection_suspected && !clause.quarantined && (
                <FirewallChip label={t(language, 'fwTampered')} />
              )}
              <h1 className="mt-3 text-[24px] font-bold leading-snug tracking-[-0.02em] text-ink-900 md:text-[28px]">
                {clauseHeading(clause.original_text, language, clause.original_text_translated) ??
                  (clause.risk_type === '해당 없음'
                    ? t(language, 'standardClauseLong')
                    : riskTypeLabel(language, clause.risk_type))}
              </h1>
              {clauseHeading(clause.original_text, language, clause.original_text_translated) && (
                <p className="mt-1.5 text-[14px] font-bold text-ink-400">
                  {clause.risk_type === '해당 없음'
                    ? t(language, 'standardClauseLong')
                    : riskTypeLabel(language, clause.risk_type)}
                </p>
              )}
            </div>
            {/* 수동 낭독 버튼 (#118) — 자동 재생 토글과 별개로 누구나 즉시 재생 가능.
                선택 언어 보이스가 기기에 없으면 숨김 (#86-①) */}
            {voiceReady && (
            <button
              type="button"
              aria-pressed={listening}
              onClick={() => {
                if (listening) {
                  stopSpeaking()
                  setListening(false)
                  return
                }
                setListening(true)
                speak(clause.explanation, language, () => setListening(false))
              }}
              className={`shrink-0 rounded-full px-3.5 py-2 text-[13px] font-bold transition-colors ${
                listening ? 'bg-ink-900 text-white' : 'bg-brand-50 text-brand-600 hover:bg-brand-100'
              }`}
            >
              {t(language, listening ? 'readAllStop' : 'listenClause')}
            </button>
            )}
          </div>

          <Section title={t(language, 'explainSimply')}>
            {(() => {
              const re = reexplained[clause.clause_id]
              const showRe = Boolean(re)
              return (
                <>
                  {showRe && (
                    <p className="mb-2 inline-flex items-center gap-1.5 rounded-lg bg-safe-50 px-2.5 py-1 text-[12px] font-bold text-safe-700">
                      <span aria-hidden>🛡️</span> {t(language, 'reVerified')}
                      {re.scores.faithfulness != null && (
                        <span className="font-semibold text-safe-700/70">
                          (faithfulness {re.scores.faithfulness.toFixed(1)})
                        </span>
                      )}
                    </p>
                  )}
                  <FormattedText text={showRe ? re.text : clause.explanation} lead />

                </>
              )
            })()}

            {/* 재설명 트리거 (#76) — judge 게이트 통과분만 반영 */}
            <div className="mt-3.5">
              {reState === 'loading' ? (
                <p className="flex items-center gap-2 text-[13px] font-semibold text-brand-600" role="status">
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-brand-200 border-t-brand-500" aria-hidden />
                  {t(language, 'reLoading')}
                </p>
              ) : (reCount[clause.clause_id] ?? 0) >= 2 ? (
                <p className="text-[13px] font-semibold text-ink-400">{t(language, 'reLimit')}</p>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => requestReexplain('easier')}
                    className="rounded-full bg-brand-50 px-3.5 py-2 text-[13px] font-bold text-brand-600 transition-colors hover:bg-brand-100"
                  >
                    {t(language, 'reEasier')}
                  </button>
                  <button
                    type="button"
                    onClick={() => requestReexplain('detailed')}
                    className="rounded-full bg-brand-50 px-3.5 py-2 text-[13px] font-bold text-brand-600 transition-colors hover:bg-brand-100"
                  >
                    {t(language, 'reDetailed')}
                  </button>
                  {reState === 'failed' && (
                    <span className="text-[13px] font-semibold text-caution-700" role="status">
                      {t(language, 'reFailed')}
                    </span>
                  )}
                </div>
              )}
            </div>
          </Section>

          {/* 방화벽 상태 (#174) — 조항 원문 바로 아래에 둔다. 사용자가 원문과
              대조하면서 "무엇이 걷어내졌는지"를 함께 봐야 하기 때문이다. */}
          {clause.verdict_withheld && (
            <p className="mt-4 rounded-xl border border-danger-500 bg-danger-50 px-4 py-3 text-[14px] font-semibold leading-relaxed text-danger-600">
              {t(language, 'fwWithheldDesc')}
            </p>
          )}
          {!!clause.original_risk_level && !clause.verdict_withheld && (
            <p className="mt-4 rounded-xl bg-ink-25 px-4 py-3 text-[14px] leading-relaxed text-ink-600">
              {t(language, 'fwOriginal', {
                level: riskLevelLabel(language, clause.original_risk_level as '안전' | '주의' | '위험'),
              })}
            </p>
          )}
          {clause.risk_level !== '안전' && !clause.verdict_withheld && (
            <Section title={t(language, 'whyCheck')}>
              {clause.analysis_failed ? (
                <p>{t(language, 'analysisFailedNote')}</p>
              ) : (
                <FormattedText text={clause.risk_evidence_translated || clause.risk_evidence} />
              )}
            </Section>
          )}

          {/* 실제 사건 각주 (#91 시그니처 기능 ①) — 큐레이션된 A등급 사례가
              있는 risk_type일 때만 노출. "동일 사건"이 아니라 "유사 사례"임을
              문구로 못 박아 단정을 피한다(자문 §7). */}
          {!!clause.related_cases?.length && (
            <section className="mt-6">
              <h2 className="text-[14px] font-bold text-ink-400">{t(language, 'relatedCases')}</h2>
              <div className="mt-2 space-y-2.5">
                {clause.related_cases.map((c) => (
                  <div
                    key={c.case_id}
                    className="rounded-2xl border border-ink-100 bg-white px-5 py-4"
                  >
                    <p className="text-[13px] font-bold text-brand-600">
                      {c.agency} {c.citation}
                    </p>
                    <p className="mt-1 text-[14px] leading-relaxed text-ink-700">{c.result}</p>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-[12px] text-ink-400">{t(language, 'relatedCasesDisclaimer')}</p>
            </section>
          )}

          <div className="mt-6 rounded-2xl border border-danger-500/20 bg-danger-50 p-5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <p className="text-[14px] font-bold text-ink-900">{t(language, 'originalText')}</p>
                {/* 부속문서에서 나온 조항은 출처를 밝힌다 — 본문과 법적 성격이 다르다 */}
                {clause.section && clause.section !== '본문' && (
                  <span className="rounded-md bg-white px-1.5 py-0.5 text-[12px] font-semibold text-ink-500">
                    {clause.section}
                  </span>
                )}
              </div>
              <CopyButton text={clause.original_text} copiedText={t(language, 'copied')} className="!bg-white">{t(language, 'copy')}</CopyButton>
            </div>
            <p className="mt-2.5 text-[15px] leading-loose text-ink-700">
              <HighlightedText text={clause.original_text} spans={clause.evidence_spans} />
            </p>
            {clause.original_text_translated && (
              <div className="mt-3 border-t border-danger-500/10 pt-3">
                <p className="text-[12px] font-bold text-ink-400">{t(language, 'translationLabel')}</p>
                <p className="mt-1 text-[14px] leading-relaxed text-ink-600">
                  {clause.original_text_translated}
                </p>
              </div>
            )}
          </div>

          <div className="mt-6">
            <h2 className="text-[14px] font-bold text-ink-400">{t(language, 'askOther')}</h2>
            {language !== 'ko' && (
              <p className="mt-1 text-[13px] text-ink-400">{t(language, 'askKoreanHint')}</p>
            )}
            <div className="mt-2 space-y-2.5">
              {questions.map((question, index) => {
                const translated = clause.check_questions_translated?.[index]
                return (
                  <div
                    key={question}
                    className="flex items-center justify-between gap-3 rounded-2xl border border-ink-100 bg-white px-5 py-4"
                  >
                    <div className="min-w-0 flex-1">
                      {/* 번역이 있으면 이해용 번역을 먼저, 상대방에게 보여줄 한국어를 아래에 */}
                      {translated && (
                        <p className="text-[14px] font-semibold leading-relaxed text-ink-900">
                          <span className="mr-1.5 rounded bg-brand-50 px-1.5 py-0.5 text-[11px] font-bold text-brand-600">
                            {t(language, 'translationLabel')}
                          </span>
                          {translated}
                        </p>
                      )}
                      <p
                        className={
                          translated
                            ? 'mt-1.5 rounded-lg bg-ink-25 px-2.5 py-1.5 text-[13px] leading-relaxed text-ink-600'
                            : 'text-[14px] leading-relaxed text-ink-700'
                        }
                      >
                        {translated && (
                          <span className="mr-1.5 font-bold text-ink-400">
                            {t(language, 'inKorean')}:
                          </span>
                        )}
                        {question}
                      </p>
                    </div>
                    <CopyButton text={question} copiedText={t(language, 'copied')}>{t(language, 'copy')}</CopyButton>
                  </div>
                )
              })}
            </div>
          </div>

          {/* 다음 행동 (과제 B) — 판정을 행동으로 연결: 협상 문구 + 구제기관.
              사람이 작성한 규칙 기반 문구(LLM 미호출)라 환각 위험이 없다
              (data/actionGuide.ts). 안전 조항, 판정 거부(verdict_withheld),
              분석 실패(analysis_failed) 조항에는 표시하지 않는다 — 근거 없는
              요구 문구는 fail-closed 원칙에 어긋나기 때문.
              TTS(#118)는 clause.explanation만 낭독하므로 이 섹션은 낭독
              흐름에 영향이 없다. */}
          {showNextActions && (
            <div className="mt-6">
              <h2 className="text-[14px] font-bold text-ink-400">{t(language, 'agNext')}</h2>

              {/* ① 협상 문구 — 근거 인용 + 유형별 요구. 한국어 유지(번역 방침:
                  상대방에게 보여주는 용도), 비한국어 UI엔 용도 라벨을 함께. */}
              <div className="mt-2 rounded-2xl border border-ink-100 bg-white p-5">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[14px] font-bold text-ink-900">{t(language, 'agAskTitle')}</p>
                  <CopyButton text={negotiation} copiedText={t(language, 'copied')}>
                    {t(language, 'copy')}
                  </CopyButton>
                </div>
                {language !== 'ko' && (
                  <p className="mt-1 text-[13px] text-ink-400">{t(language, 'agKoreanHint')}</p>
                )}
                <p className="mt-2.5 rounded-xl bg-ink-25 px-4 py-3 text-[14px] leading-relaxed text-ink-700">
                  {negotiation}
                </p>
                <p className="mt-2 text-[12px] text-ink-400">{t(language, 'agDisclaimer')}</p>
              </div>

              {/* ② 구제기관 — 문서 도메인 매칭 (기관 데이터는 Done 화면과
                  actionGuide.ts AGENCIES를 공유해 어긋나지 않는다) */}
              <div className="mt-2.5 rounded-2xl border border-ink-100 bg-white p-5">
                <p className="text-[14px] font-bold text-ink-900">{t(language, 'agAgencyTitle')}</p>
                <div className="mt-2.5 space-y-2.5">
                  {agenciesForDomain(domain).map((agency) => (
                    <div
                      key={agency.name}
                      className="flex flex-col gap-2 rounded-xl bg-ink-25 px-4 py-3 md:flex-row md:items-center md:justify-between"
                    >
                      <div className="min-w-0">
                        <p className="text-[14px] font-bold text-ink-900">{agency.name}</p>
                        <p className="mt-0.5 text-[13px] leading-relaxed text-ink-500">
                          {t(language, agency.descKey)}
                        </p>
                      </div>
                      {agency.phone && (
                        <a
                          href={`tel:${agency.phone}`}
                          className="shrink-0 self-start rounded-lg bg-white px-2.5 py-1.5 text-[13px] font-bold text-ink-600 hover:bg-ink-50 md:self-auto"
                        >
                          {t(language, 'doCall')} {agency.phone}
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="mt-9 flex flex-col-reverse justify-between gap-2.5 md:flex-row">
            <Button variant="secondary" onClick={onBack}>
              {t(language, 'otherClauses')}
            </Button>
            <Button onClick={onDone}>{t(language, 'finishDetail')}</Button>
          </div>
        </article>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="text-[14px] font-bold text-ink-400">{title}</h2>
      <div className="mt-2 rounded-2xl bg-ink-25 p-5 text-[15px] leading-loose text-ink-700">
        {children}
      </div>
    </section>
  )
}
