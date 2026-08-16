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
): Promise<AnalyzeResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('persona', persona)

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
