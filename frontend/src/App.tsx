import { useEffect, useRef, useState } from 'react'
import {
  analyzeContractStream,
  analyzeFileStream,
  type AnalyzeResponse,
  type ClauseResult,
  type Language,
  type Persona,
} from './api'
import { Logo } from './components/ui'
import { LANGUAGES, t } from './i18n'
import { saveRecord, type SavedRecord } from './records'
import type { DemoSample } from './data/samples'
import type { ClauseResult as ClauseResultType } from './api'
import { DetailScreen } from './screens/Detail'
import { DoneScreen } from './screens/Done'
import { ExtractScreen } from './screens/Extract'
import { ApiInfoScreen } from './screens/ApiInfo'
import { LandingScreen } from './screens/Landing'
import { PersonaScreen } from './screens/Persona'
import { ProgressScreen } from './screens/Progress'
import { SummaryScreen } from './screens/Summary'
import { UploadScreen } from './screens/Upload'
import { RecordsScreen } from './screens/Records'

import { LearnScreen } from './screens/Learn'

// KRDS --krds-zoom-small/medium/large/xlarge/xxlarge (common.css)
const ZOOM_LEVELS = [0.9, 1, 1.1, 1.3, 1.5]

type Screen =
  | 'landing'
  | 'api'
  | 'learn'
  | 'records'
  | 'upload'
  | 'extract'
  | 'persona'
  | 'progress'
  | 'summary'
  | 'detail'
  | 'done'

type InputMode = 'pdf' | 'text'

export default function App() {
  const [screen, setScreen] = useState<Screen>('landing')
  const [mode, setMode] = useState<InputMode>('pdf')
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState('')
  const [persona, setPersona] = useState<Persona>('adult')
  const [domain, setDomain] = useState('') // 사용자 선택 문서 유형 ('' = 모름)
  const [language, setLanguage] = useState<Language>('ko')

  // 접근성 설정
  // 글자·화면 크기 5단계 (KRDS --krds-zoom-*: 0.9/1/1.1/1.3/1.5) —
  // KRDS 사이트 우상단 '글자·화면 설정'과 같은 사고방식, 선택값은 저장.
  const [zoom, setZoom] = useState<number>(() => {
    const saved = Number(localStorage.getItem('jmjm_zoom'))
    return ZOOM_LEVELS.includes(saved) ? saved : 1
  })
  const [highContrast, setHighContrast] = useState(false)
  const [voiceGuide, setVoiceGuide] = useState(false)

  // 분석 상태
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<AnalyzeResponse | null>(null)
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null)

  // 새로고침/재방문 후 히스토리로 결과 화면에 진입하면 데이터가 없다 — 홈으로 폴백
  const hasResultsRef = useRef(false)

  // 스트리밍 진행 상태 (텍스트 분석 경로에서만 채워짐)
  const [streamProgress, setStreamProgress] = useState<{ done: number; total: number } | null>(null)
  // 결과가 생성된 언어 — 결과를 보다가 언어를 바꾸면 UI 라벨만 바뀌고 설명은
  // 분석 시점 언어로 남는다. 불일치를 감지해 재분석 안내 배너를 띄운다.
  const [analyzedLanguage, setAnalyzedLanguage] = useState<Language>('ko')
  // 사람 평가 지표(자문 §6): 결과 표시 시각 — 만족도 응답까지의 '읽는 시간' 측정용
  const [resultsShownAt, setResultsShownAt] = useState<number | null>(null)
  // judge 재시도로 조항이 다시 생성되는 중 — 카드가 소리 없이 교체되는 대신
  // 배너로 알린다 (#101 '새로고침 느낌' 피드백)
  const [retrying, setRetrying] = useState(false)
  // 옵트인 로컬 기록 (#102 v1) — 현재 결과의 저장 여부
  const [recordSaved, setRecordSaved] = useState(false)
  const [savedRecordId, setSavedRecordId] = useState<string | null>(null)
  const [streamedClauses, setStreamedClauses] = useState<ClauseResult[]>([])

  // 스트리밍 중엔 완료된 조항(clause_id 순 정렬)을, 완료 후엔 확정 결과를 쓴다.
  // 실패 시 가짜 예시(SAMPLE_RESULTS)를 보여주던 경로는 제거 — 오류는 오류로
  // 안내하고 다시 시도하게 한다 (심사 중 가짜 결과 노출 방지).
  const sortedStreamed = [...streamedClauses].sort((a, b) =>
    a.clause_id.localeCompare(b.clause_id),
  )
  const streamingLive = loading && streamProgress !== null
  const results: ClauseResultType[] = data?.results.length
    ? data.results
    : streamingLive
      ? sortedStreamed
      : []
  const clauseCount = data?.clause_count ?? streamProgress?.total ?? 0
  hasResultsRef.current = results.length > 0

  // 글자·화면 크기: KRDS zoom 토큰 값을 문서 루트에 적용 — 텍스트만이 아니라
  // 레이아웃·아이콘·터치 타깃이 함께 커져 저시력 사용자에게 일관적이다.
  // 결과가 확정되면 읽기 시작 시각 기록 (사람 평가 소요시간 지표)
  useEffect(() => {
    if (data) setResultsShownAt(Date.now())
  }, [data])

  // 글자 크게: rem 기준(html font-size)을 키워 전체 화면에 적용
  useEffect(() => {
    document.documentElement.style.zoom = String(zoom)
    localStorage.setItem('jmjm_zoom', String(zoom))
  }, [zoom])

  // 접근성(#82): 화면 전환 시 스크린리더 포커스를 새 화면 제목으로 이동 —
  // SPA는 페이지 로드가 없어 전환을 알리지 않으면 리더가 침묵한다
  useEffect(() => {
    // rAF는 백그라운드 탭에서 정지되므로 setTimeout 사용 — effect 시점에
    // 이미 커밋이 끝나 있어 지연 0으로 충분하다
    const timer = setTimeout(() => {
      const heading = document.querySelector<HTMLElement>('main h1')
      if (heading) {
        heading.setAttribute('tabindex', '-1')
        heading.focus({ preventScroll: true })
      }
    }, 0)
    return () => clearTimeout(timer)
  }, [screen])

  // 화면 전환을 브라우저 히스토리에 쌓는다 — 뒤로가기가 홈으로 튕기며 분석
  // 결과까지 날리던 문제의 수정. popstate로 앱 내 화면 이동으로 처리한다.
  const go = (next: Screen) => {
    window.history.pushState({ screen: next }, '')
    setScreen(next)
    window.scrollTo({ top: 0 })
  }

  useEffect(() => {
    window.history.replaceState({ screen: 'landing' }, '')
    const onPop = (event: PopStateEvent) => {
      const target = (event.state?.screen as Screen) ?? 'landing'
      const needsData = target === 'summary' || target === 'detail' || target === 'done'
      setScreen(needsData && !hasResultsRef.current ? 'landing' : target)
      window.scrollTo({ top: 0 })
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const runAnalysis = async () => {
    setError(null)
    setLoading(true)
    setStreamProgress(null)
    setStreamedClauses([])
    // 재분석(언어 변경 등) 시 이전 결과를 비운다 — 남겨두면 results가
    // data?.results를 우선해 스트리밍 중에도 옛 결과가 계속 표시된다
    setData(null)
    setAnalyzedLanguage(language)
    setRetrying(false)
    setRecordSaved(false)
    setSavedRecordId(null)
    go('progress')

    try {
      if (mode === 'text' && text.trim()) {
        // 텍스트 경로는 조항별 스트리밍 — 결과 화면으로 즉시 이동해
        // 끝난 조항부터 카드로 쌓이고 '자세히 보기'도 바로 동작한다
        setStreamProgress({ done: 0, total: 0 })
        go('summary')
        setData(
          await analyzeContractStream(text, persona, language, {
            onMeta: (meta) => setStreamProgress({ done: 0, total: meta.clause_count }),
            onClause: ({ done, total, revision, result }) => {
              setStreamProgress({ done, total })
              setStreamedClauses((prev) => [
                ...prev.filter((c) => c.clause_id !== result.clause_id),
                { ...result, revision },
              ])
            },
            onRetry: () => setRetrying(true),
          }, domain),
        )
      } else if (mode === 'pdf' && file) {
        // 파일 경로도 동일한 스트리밍 UX — 텍스트 추출(OCR)까지는 진행 화면을
        // 유지하고, 조항 목록이 확정되는 meta부터 결과 화면에서 카드가 쌓인다
        setData(
          await analyzeFileStream(file, persona, language, {
            onMeta: (meta) => {
              setStreamProgress({ done: 0, total: meta.clause_count })
              go('summary')
            },
            onClause: ({ done, total, result }) => {
              setStreamProgress({ done, total })
              setStreamedClauses((prev) => [
                ...prev.filter((c) => c.clause_id !== result.clause_id),
                result,
              ])
            },
          }, domain),
        )
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t(language, 'requestFailed'))
      setStreamProgress(null)
      go('progress') // 오류 안내와 재시도 버튼은 Progress 화면이 담당
    } finally {
      setLoading(false)
      setRetrying(false)
    }
  }

  const restart = () => {
    setData(null)
    setError(null)
    setFile(null)
    setText('')
    setDomain('')
    setSelectedClauseId(null)
    go('upload')
  }

  // 원클릭 데모 샘플 (#81): 조항·유형·(시나리오6) 페르소나까지 한 번에 세팅.
  // 파일 샘플(PDF·사진)은 번들된 정적 자산을 File로 만들어 실제 업로드 경로 그대로 태운다.
  const applySample = async (sample: DemoSample) => {
    setDomain(sample.domain)
    if (sample.persona) setPersona(sample.persona)
    if (sample.kind === 'file' && sample.fileUrl) {
      setMode('pdf')
      setText('')
      try {
        const blob = await fetch(sample.fileUrl).then((r) => r.blob())
        setFile(new File([blob], sample.fileName ?? 'sample', { type: sample.fileType }))
      } catch {
        setFile(null)
      }
    } else {
      setMode('text')
      setFile(null)
      setText(sample.text ?? '')
    }
  }

  const openRecord = (record: SavedRecord) => {
    setData(record.data)
    setDomain(record.domain)
    setRecordSaved(true) // 이미 저장된 기록이므로 중복 저장 버튼 숨김
    setSavedRecordId(record.id) // Done 화면 '삭제' 시 이 기록도 함께 지우기 위해
    go('summary')
  }

  const openDetail = (clauseId: string) => {
    setSelectedClauseId(clauseId)
    go('detail')
  }

  return (
    <div className={`min-h-screen bg-white ${highContrast ? 'hc' : ''}`}>
      {/* 스크린리더·키보드 사용자용 스킵 링크 (#82 2차) — 포커스될 때만 보임 */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-xl focus:bg-brand-500 focus:px-4 focus:py-2 focus:text-white"
      >
        {t(language, 'skipToMain')}
      </a>
      <header className="sticky top-0 z-20 border-b border-ink-50 bg-white/90 backdrop-blur-md print:hidden">
        {/* 좁은 폭(375px)에서는 컨트롤이 둘째 줄로 내려간다 — 고정 h-16이면
            zoom 스테퍼가 추가된 뒤 오버플로로 '또렷하게'가 잘림 (실측) */}
        <div className="mx-auto flex min-h-16 max-w-6xl flex-wrap items-center justify-between gap-y-1 px-4 py-1.5 md:px-6">
          <Logo onClick={() => go('landing')} />
          <div className="flex flex-wrap items-center gap-1.5 md:gap-2">
            <button
              type="button"
              aria-pressed={screen === 'learn'}
              onClick={() => go('learn')}
              className={`rounded-full px-3.5 py-2 text-[13px] font-bold transition-colors ${
                screen === 'learn' ? 'bg-ink-900 text-white' : 'bg-ink-50 text-ink-600 hover:bg-ink-100'
              }`}
            >
              {t(language, 'lnNav')}
            </button>
            <label className="flex items-center gap-1.5 rounded-full bg-ink-50 px-3.5 py-2 text-[13px] font-bold text-ink-600 transition-colors hover:bg-ink-100">
              <select
                aria-label="언어 선택 / Language"
                value={language}
                onChange={(e) => setLanguage(e.target.value as Language)}
                className="cursor-pointer appearance-none bg-transparent pr-1 font-bold outline-none"
              >
                {LANGUAGES.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            {/* 글자·화면 크기 (KRDS zoom 5단계) — 값은 aria-live로 낭독 */}
            <div
              role="group"
              aria-label={t(language, 'zoomLabel')}
              className="flex items-center gap-0.5 rounded-full bg-ink-50 px-1.5 py-1 text-[13px] font-bold text-ink-600"
            >
              <button
                type="button"
                aria-label={t(language, 'zoomOut')}
                disabled={zoom === ZOOM_LEVELS[0]}
                onClick={() => setZoom(ZOOM_LEVELS[Math.max(0, ZOOM_LEVELS.indexOf(zoom) - 1)])}
                className="rounded-full px-2 py-1 hover:bg-ink-100 disabled:text-ink-300"
              >
                가−
              </button>
              <span aria-live="polite" className="min-w-[42px] text-center tabular-nums">
                {Math.round(zoom * 100)}%
              </span>
              <button
                type="button"
                aria-label={t(language, 'zoomIn')}
                disabled={zoom === ZOOM_LEVELS[ZOOM_LEVELS.length - 1]}
                onClick={() =>
                  setZoom(ZOOM_LEVELS[Math.min(ZOOM_LEVELS.length - 1, ZOOM_LEVELS.indexOf(zoom) + 1)])
                }
                className="rounded-full px-2 py-1 hover:bg-ink-100 disabled:text-ink-300"
              >
                가+
              </button>
            </div>
            <button
              type="button"
              onClick={() => go('records')}
              className="rounded-full bg-ink-50 px-3.5 py-2 text-[13px] font-bold text-ink-600 transition-colors hover:bg-ink-100"
            >
              🗂 {t(language, 'rcNav')}
            </button>
            <button
              type="button"
              aria-pressed={highContrast}
              onClick={() => setHighContrast((value) => !value)}
              className={`rounded-full px-4 py-2 text-[13px] font-bold transition-colors ${
                highContrast
                  ? 'bg-ink-900 text-white'
                  : 'bg-ink-50 text-ink-600 hover:bg-ink-100'
              }`}
            >
              {t(language, 'hcToggle')}
            </button>
          </div>
        </div>
      </header>

      <main id="main">
        {/* 결과 열람 중 언어 변경 감지 — 설명은 분석 시점 언어로 생성되므로
            바꾼 언어로 받으려면 재분석이 필요하다. 입력(텍스트·파일)은 상태에
            남아 있어 버튼 한 번으로 같은 계약서를 다시 분석한다. */}
        {Boolean(data) && !loading && language !== analyzedLanguage &&
          (screen === 'summary' || screen === 'detail') && (
          <div className="mx-auto max-w-3xl px-6 pt-6">
            <div className="flex flex-col gap-3 rounded-2xl border border-brand-500/20 bg-brand-50 px-5 py-4 md:flex-row md:items-center md:justify-between">
              <p className="text-[14px] font-semibold leading-relaxed text-ink-700">
                {t(language, 'langMismatch')}
              </p>
              <button
                type="button"
                onClick={runAnalysis}
                className="shrink-0 rounded-xl bg-brand-500 px-4 py-2.5 text-[14px] font-bold text-white transition-colors hover:bg-brand-600"
              >
                {t(language, 'reanalyze')}
              </button>
            </div>
          </div>
        )}
        {screen === 'records' && <RecordsScreen language={language} onOpen={openRecord} />}
        {screen === 'api' && <ApiInfoScreen language={language} onBack={() => go('landing')} />}
        {screen === 'landing' && (
          <LandingScreen
            language={language}
            onStart={() => go('upload')}
            onApiInfo={() => go('api')}
          />
        )}
        {screen === 'learn' && <LearnScreen language={language} onStart={() => go('upload')} />}
        {screen === 'upload' && (
          <UploadScreen
            mode={mode}
            file={file}
            text={text}
            domain={domain}
            language={language}
            onModeChange={setMode}
            onFileChange={setFile}
            onTextChange={setText}
            onDomainChange={setDomain}
            onSampleSelect={applySample}
            onNext={() => go('extract')}
          />
        )}
        {screen === 'extract' && (
          <ExtractScreen
            file={file}
            mode={mode}
            text={text}
            language={language}
            onPrev={() => go('upload')}
            onNext={() => go('persona')}
          />
        )}
        {screen === 'persona' && (
          <PersonaScreen
            persona={persona}
            language={language}
            largeText={zoom > 1}
            highContrast={highContrast}
            voiceGuide={voiceGuide}
            onPersonaChange={setPersona}
            onLanguageChange={setLanguage}
            onToggleLargeText={() => setZoom((value) => (value > 1 ? 1 : 1.3))}
            onToggleHighContrast={() => setHighContrast((value) => !value)}
            onToggleVoiceGuide={() => setVoiceGuide((value) => !value)}
            onPrev={() => go('extract')}
            onStartAnalysis={runAnalysis}
          />
        )}
        {screen === 'progress' && (
          <ProgressScreen
            language={language}
            loading={loading}
            error={error}
            streamProgress={streamProgress}
            streamedClauses={streamedClauses}
            onCancel={() => go('persona')}
            onRetry={runAnalysis}
            onShowResult={() => go('summary')}
          />
        )}
        {screen === 'summary' && (
          <SummaryScreen
            clauseCount={clauseCount}
            results={results}
            language={language}
            liveProgress={streamingLive ? streamProgress : null}
            retrying={retrying}
            recordSaved={recordSaved}
            onSaveRecord={
              data
                ? () => {
                    const record = saveRecord(data, { domain, language })
                    setRecordSaved(true)
                    setSavedRecordId(record.id)
                  }
                : undefined
            }
            domain={domain}
            persona={persona}
            judgeScores={data?.judge_scores ?? {}}
            retryCount={data?.retry_count ?? 0}
            needsReview={data?.needs_review ?? false}
            warnings={data?.parse_warnings ?? []}
            warningCodes={data?.parse_warning_codes ?? []}
            onSelectClause={openDetail}
            onDone={() => go('done')}
          />
        )}
        {screen === 'detail' && (
          <DetailScreen
            clauseId={selectedClauseId ?? results[0].clause_id}
            results={results}
            voiceGuide={voiceGuide}
            language={language}
            persona={persona}
            onSelectClause={setSelectedClauseId}
            onBack={() => go('summary')}
            onDone={() => go('done')}
          />
        )}
        {screen === 'done' && (
          <DoneScreen
            results={results}
            language={language}
            resultsShownAt={resultsShownAt}
            recordSaved={recordSaved}
            savedRecordId={savedRecordId}
            onRestart={restart}
          />
        )}
      </main>
    </div>
  )
}
