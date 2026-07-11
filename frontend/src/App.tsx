import { useEffect, useState } from 'react'
import { analyzeContract, analyzePdf, type AnalyzeResponse, type Persona } from './api'
import { Logo } from './components/ui'
import { SAMPLE_RESULTS } from './data/sample'
import { DetailScreen } from './screens/Detail'
import { DoneScreen } from './screens/Done'
import { ExtractScreen } from './screens/Extract'
import { LandingScreen } from './screens/Landing'
import { PersonaScreen } from './screens/Persona'
import { ProgressScreen } from './screens/Progress'
import { SummaryScreen } from './screens/Summary'
import { UploadScreen } from './screens/Upload'

type Screen =
  | 'landing'
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

  // 접근성 설정
  const [largeText, setLargeText] = useState(false)
  const [highContrast, setHighContrast] = useState(false)
  const [voiceGuide, setVoiceGuide] = useState(false)

  // 분석 상태
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<AnalyzeResponse | null>(null)
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null)

  const results = data?.results.length ? data.results : SAMPLE_RESULTS
  const clauseCount = data?.clause_count ?? 16
  const isSample = !data

  // 글자 크게: rem 기준(html font-size)을 키워 전체 화면에 적용
  useEffect(() => {
    document.documentElement.style.fontSize = largeText ? '18px' : '16px'
  }, [largeText])

  const go = (next: Screen) => {
    setScreen(next)
    window.scrollTo({ top: 0 })
  }

  const runAnalysis = async () => {
    setError(null)
    setLoading(true)
    go('progress')

    try {
      if (mode === 'text' && text.trim()) {
        setData(await analyzeContract(text, persona))
      } else if (mode === 'pdf' && file) {
        setData(await analyzePdf(file, persona))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '분석 요청에 실패했어요.')
    } finally {
      setLoading(false)
    }
  }

  const restart = () => {
    setData(null)
    setError(null)
    setFile(null)
    setText('')
    setSelectedClauseId(null)
    go('upload')
  }

  const openDetail = (clauseId: string) => {
    setSelectedClauseId(clauseId)
    go('detail')
  }

  return (
    <div className={`min-h-screen bg-white ${highContrast ? 'hc' : ''}`}>
      <header className="sticky top-0 z-20 border-b border-ink-50 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Logo onClick={() => go('landing')} />
          <button
            type="button"
            aria-pressed={largeText}
            onClick={() => setLargeText((value) => !value)}
            className={`rounded-full px-4 py-2 text-[13px] font-bold transition-colors ${
              largeText
                ? 'bg-ink-900 text-white'
                : 'bg-ink-50 text-ink-600 hover:bg-ink-100'
            }`}
          >
            가 글자 크게
          </button>
        </div>
      </header>

      <main>
        {screen === 'landing' && <LandingScreen onStart={() => go('upload')} />}
        {screen === 'upload' && (
          <UploadScreen
            mode={mode}
            file={file}
            text={text}
            onModeChange={setMode}
            onFileChange={setFile}
            onTextChange={setText}
            onNext={() => go('extract')}
          />
        )}
        {screen === 'extract' && (
          <ExtractScreen
            file={file}
            mode={mode}
            text={text}
            onPrev={() => go('upload')}
            onNext={() => go('persona')}
          />
        )}
        {screen === 'persona' && (
          <PersonaScreen
            persona={persona}
            largeText={largeText}
            highContrast={highContrast}
            voiceGuide={voiceGuide}
            onPersonaChange={setPersona}
            onToggleLargeText={() => setLargeText((value) => !value)}
            onToggleHighContrast={() => setHighContrast((value) => !value)}
            onToggleVoiceGuide={() => setVoiceGuide((value) => !value)}
            onPrev={() => go('extract')}
            onStartAnalysis={runAnalysis}
          />
        )}
        {screen === 'progress' && (
          <ProgressScreen
            loading={loading}
            error={error}
            onCancel={() => go('persona')}
            onShowResult={() => go('summary')}
          />
        )}
        {screen === 'summary' && (
          <SummaryScreen
            clauseCount={clauseCount}
            results={results}
            isSample={isSample}
            onSelectClause={openDetail}
            onDone={() => go('done')}
          />
        )}
        {screen === 'detail' && (
          <DetailScreen
            clauseId={selectedClauseId ?? results[0].clause_id}
            results={results}
            voiceGuide={voiceGuide}
            onSelectClause={setSelectedClauseId}
            onBack={() => go('summary')}
            onDone={() => go('done')}
          />
        )}
        {screen === 'done' && <DoneScreen results={results} onRestart={restart} />}
      </main>
    </div>
  )
}
