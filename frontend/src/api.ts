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
