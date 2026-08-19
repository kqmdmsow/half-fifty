// 백엔드(Spring Boot, 8080) API 호출 모듈.
// 백엔드 응답 스키마와 1:1 대응하는 타입 정의.

import type { LangCode } from './i18n'

export type Persona = 'adult' | 'senior' | 'foreigner'
export type Language = LangCode

export interface ClauseResult {
  clause_id: string
  original_text: string
  explanation: string
  risk_level: '안전' | '주의' | '위험'
  risk_type: string
  risk_evidence: string
  check_questions: string[]
  // 비한국어 언어 선택 시에만 채워짐 — 한국어 원문·질문에 번역 병기용
  original_text_translated?: string | null
  check_questions_translated?: string[] | null
}

export interface AnalyzeResponse {
  clause_count: number
  parse_warnings?: string[]
  retry_count: number
  needs_review: boolean
  judge_scores: Record<string, number>
  results: ClauseResult[]
}

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8080'



export async function analyzeContract(
  text: string,
  persona: Persona,
  language: Language = 'ko',
  domain = '',
): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE_URL}/api/contracts/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, persona, language, domain }),
  })
  if (!res.ok) {
    // 백엔드 표준 에러(JSON {message})가 있으면 그대로 사용자에게 (#52)
    const message = await res.json().then((d) => d?.message).catch(() => null)
    throw new Error(message ?? `분석 요청 실패 (${res.status})`)
  }
  return res.json()
}

// ---- 조항별 점진 스트리밍 (NDJSON) -------------------------------------
// 이벤트 계약: agent src/stream.py docstring 참조.
// clause 이벤트는 Judge 검증 전 결과 — UI는 '검증 중'으로 표시하고
// judge 이벤트가 와야 확정이다.

export interface StreamHandlers {
  // 파일 경로 전용: 텍스트 추출(OCR 포함) 시작 알림
  onExtract?: () => void
  onMeta?: (meta: { clause_count: number; parse_warnings: string[] }) => void
  onClause?: (payload: { done: number; total: number; revision: number; result: ClauseResult }) => void
  onRetry?: (payload: { retry_count: number; reason: string }) => void
}

export async function analyzeContractStream(
  text: string,
  persona: Persona,
  language: Language,
  handlers: StreamHandlers,
  domain = '',
): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE_URL}/api/contracts/analyze-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, persona, language, domain }),
  })
  if (!res.ok || !res.body) {
    const message = res.ok ? null : await res.json().then((d) => d?.message).catch(() => null)
    throw new Error(message ?? `분석 요청 실패 (${res.status})`)
  }
  return consumeAnalysisStream(res, handlers)
}

// 파일(PDF·사진) 업로드도 동일한 조항별 스트리밍 — 추출 실패는 스트림이 열린
// 뒤라 HTTP 상태 대신 {"event":"error"}로 도착한다 (아래 consumeAnalysisStream).
export async function analyzeFileStream(
  file: File,
  persona: Persona,
  language: Language,
  handlers: StreamHandlers,
  domain = '',
): Promise<AnalyzeResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('persona', persona)
  formData.append('language', language)
  formData.append('domain', domain)

  const res = await fetch(`${BASE_URL}/api/contracts/analyze-file-stream`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok || !res.body) {
    if (res.status === 415) {
      throw new Error('PDF나 jpg/png/webp 사진만 올릴 수 있어요.')
    }
    if (res.status === 413) {
      throw new Error('파일은 10MB 이하만 올릴 수 있어요.')
    }
    throw new Error(`분석 요청 실패 (${res.status})`)
  }
  return consumeAnalysisStream(res, handlers)
}

async function consumeAnalysisStream(
  res: Response,
  handlers: StreamHandlers,
): Promise<AnalyzeResponse> {
  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  let clauseCount = 0
  let warnings: string[] = []
  const resultsById = new Map<string, ClauseResult>()
  // TS는 클로저 내부 할당으로 let 변수의 narrowing을 못 풀므로 홀더 객체를 쓴다
  const final: {
    judge: { judge_scores: Record<string, number>; needs_review: boolean; retry_count: number } | null
  } = { judge: null }

  const handleLine = (line: string) => {
    if (!line.trim()) return
    const event = JSON.parse(line)
    switch (event.event) {
      case 'extract':
        handlers.onExtract?.()
        break
      case 'error':
        // 파일 텍스트 추출 실패 — 스트림이 열린 뒤라 HTTP 상태 대신 이벤트로 도착
        throw new Error('파일에서 글자를 읽지 못했어요. 계약서가 잘 보이게 다시 올려주세요.')
      case 'meta':
        clauseCount = event.clause_count
        warnings = event.parse_warnings ?? []
        handlers.onMeta?.(event)
        break
      case 'clause':
        resultsById.set(event.result.clause_id, event.result)
        handlers.onClause?.(event)
        break
      case 'retry':
        handlers.onRetry?.(event)
        break
      case 'judge':
        final.judge = event
        break
    }
  }

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    lines.forEach(handleLine)
  }
  if (buffer.trim()) handleLine(buffer)

  // clause_id 순서로 정렬해 조립 (clause_001, clause_002, ...)
  const results = [...resultsById.values()].sort((a, b) =>
    a.clause_id.localeCompare(b.clause_id),
  )
  return {
    clause_count: clauseCount || results.length,
    parse_warnings: warnings,
    retry_count: final.judge?.retry_count ?? 0,
    needs_review: final.judge?.needs_review ?? false,
    judge_scores: final.judge?.judge_scores ?? {},
    results,
  }
}

export async function analyzePdf(
  file: File,
  persona: Persona,
  language: Language = 'ko',
  domain = '',
): Promise<AnalyzeResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('persona', persona)
  formData.append('language', language)
  formData.append('domain', domain)

  const res = await fetch(`${BASE_URL}/api/contracts/analyze-pdf`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    if (res.status === 422) {
      throw new Error('PDF에서 글자를 읽지 못했어요. 스캔본이면 사진이 선명한지 확인해주세요.')
    }
    if (res.status === 415) {
      throw new Error('PDF 파일만 업로드할 수 있어요.')
    }
    throw new Error(`PDF 분석 요청 실패 (${res.status})`)
  }
  return res.json()
}

export async function analyzeImage(
  file: File,
  persona: Persona,
  language: Language = 'ko',
  domain = '',
): Promise<AnalyzeResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('persona', persona)
  formData.append('language', language)
  formData.append('domain', domain)

  const res = await fetch(`${BASE_URL}/api/contracts/analyze-image`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    if (res.status === 422) {
      throw new Error('사진에서 글자를 읽지 못했어요. 계약서가 잘 보이게 다시 찍어주세요.')
    }
    if (res.status === 415) {
      throw new Error('jpg/png/webp 사진만 올릴 수 있어요.')
    }
    throw new Error(`분석 요청 실패 (${res.status})`)
  }
  return res.json()
}
