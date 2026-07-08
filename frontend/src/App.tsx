import { useState } from 'react'
import { analyzeContract, analyzePdf, type AnalyzeResponse, type Persona } from './api'

type InputMode = 'text' | 'pdf'

// 위험도별 배지 색상
const RISK_STYLE: Record<string, string> = {
  안전: 'bg-emerald-100 text-emerald-800',
  주의: 'bg-amber-100 text-amber-800',
  위험: 'bg-red-100 text-red-800',
}

export default function App() {
  const [mode, setMode] = useState<InputMode>('text')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [persona, setPersona] = useState<Persona>('adult')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<AnalyzeResponse | null>(null)

  const handleAnalyze = async () => {
    if (mode === 'text' && !text.trim()) {
      setError('계약서 내용을 입력해 주세요.')
      return
    }
    if (mode === 'pdf' && !file) {
      setError('PDF 파일을 선택해 주세요.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res =
        mode === 'text' ? await analyzeContract(text, persona) : await analyzePdf(file!, persona)
      setData(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : '알 수 없는 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-4xl px-6 py-5">
          <h1 className="text-xl font-bold text-slate-900">
            계약서 위험 안내 <span className="font-normal text-slate-400">· 하프피프티</span>
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            계약서를 붙여넣으면 조항별로 쉬운 설명, 위험 여부, 확인할 질문을 알려드립니다.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        {/* 입력 영역 */}
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <div className="mb-3 flex gap-2">
            {(['text', 'pdf'] as InputMode[]).map((m) => (
              <button
                key={m}
                onClick={() => {
                  setMode(m)
                  setError(null)
                }}
                className={`rounded-full px-4 py-1.5 text-sm ${
                  mode === m
                    ? 'bg-slate-900 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {m === 'text' ? '텍스트 붙여넣기' : 'PDF 업로드'}
              </button>
            ))}
          </div>

          {mode === 'text' ? (
            <textarea
              className="h-48 w-full resize-y rounded-md border border-slate-300 p-3 text-sm focus:border-slate-500 focus:outline-none"
              placeholder="계약서 내용을 붙여넣어 주세요. (예: 제1조 ...)"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          ) : (
            <div className="flex h-48 w-full flex-col items-center justify-center rounded-md border border-dashed border-slate-300 p-3 text-sm">
              <input
                id="pdf-input"
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <label
                htmlFor="pdf-input"
                className="cursor-pointer rounded-md bg-slate-100 px-4 py-2 text-slate-700 hover:bg-slate-200"
              >
                PDF 파일 선택
              </label>
              <p className="mt-3 text-slate-500">
                {file ? file.name : '텍스트 레이어가 있는 디지털 PDF만 지원합니다 (스캔본 제외)'}
              </p>
            </div>
          )}

          <div className="mt-4 flex items-center justify-between">
            <div className="flex gap-2">
              {(['adult', 'senior'] as Persona[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPersona(p)}
                  className={`rounded-full px-4 py-1.5 text-sm ${
                    persona === p
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {p === 'adult' ? '일반 성인' : '고령층'}
                </button>
              ))}
            </div>
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="rounded-md bg-slate-900 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {loading ? '분석 중...' : '계약서 분석하기'}
            </button>
          </div>
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </section>

        {/* 결과 영역 */}
        {data && (
          <section className="mt-8">
            <div className="mb-4 flex items-center gap-3 text-sm text-slate-500">
              <span>조항 {data.clause_count}개</span>
              <span>·</span>
              <span>재생성 {data.retry_count}회</span>
              {data.needs_review && (
                <span className="rounded bg-red-100 px-2 py-0.5 text-red-700">
                  주의 필요: 품질 기준 미달
                </span>
              )}
            </div>

            <div className="space-y-4">
              {data.results.map((r) => (
                <article
                  key={r.clause_id}
                  className="rounded-lg border border-slate-200 bg-white p-5"
                >
                  <div className="flex items-start justify-between gap-4">
                    <p className="text-sm text-slate-400">{r.original_text}</p>
                    <span
                      className={`shrink-0 rounded-full px-3 py-0.5 text-xs font-medium ${
                        RISK_STYLE[r.risk_level] ?? 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {r.risk_level}
                      {r.risk_type !== '해당 없음' && ` · ${r.risk_type}`}
                    </span>
                  </div>

                  <p className="mt-3 text-sm leading-relaxed text-slate-800">
                    {r.explanation}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">근거: {r.risk_evidence}</p>

                  {r.check_questions.length > 0 && (
                    <div className="mt-3 rounded-md bg-slate-50 p-3">
                      <p className="text-xs font-medium text-slate-600">확인해 보세요</p>
                      <ul className="mt-1 space-y-1">
                        {r.check_questions.map((q, i) => (
                          <li key={i} className="text-sm text-slate-700">
                            · {q}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </article>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
