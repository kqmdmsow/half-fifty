// 백엔드(Spring Boot, 8080) API 호출 모듈.
// 백엔드 응답 스키마와 1:1 대응하는 타입 정의.

export type Persona = 'adult' | 'senior'

export interface ClauseResult {
  clause_id: string
  original_text: string
  explanation: string
  risk_level: '안전' | '주의' | '위험'
  risk_type: string
  risk_evidence: string
  check_questions: string[]
}

export interface AnalyzeResponse {
  clause_count: number
  retry_count: number
  needs_review: boolean
  judge_scores: Record<string, number>
  results: ClauseResult[]
}

const BASE_URL = 'http://localhost:8080'

// 에이전트(Python, 8000) 직접 호출용 — PDF 업로드는 백엔드를 거치지 않고
// 에이전트에 바로 보낸다 (백엔드는 아직 이 경로를 프록시하지 않음).
const AGENT_BASE_URL = 'http://localhost:8000'

export async function analyzeContract(
  text: string,
  persona: Persona,
): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE_URL}/api/contracts/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, persona }),
  })
  if (!res.ok) {
    throw new Error(`분석 요청 실패 (${res.status})`)
  }
  return res.json()
}

export async function analyzePdf(
  file: File,
  persona: Persona,
): Promise<AnalyzeResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('persona', persona)

  const res = await fetch(`${AGENT_BASE_URL}/analyze-pdf`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    if (res.status === 422) {
      throw new Error('텍스트 추출이 안 되는 PDF예요. 스캔본이면 지원 예정입니다.')
    }
    if (res.status === 415) {
      throw new Error('PDF 파일만 업로드할 수 있어요.')
    }
    throw new Error(`PDF 분석 요청 실패 (${res.status})`)
  }
  return res.json()
}
