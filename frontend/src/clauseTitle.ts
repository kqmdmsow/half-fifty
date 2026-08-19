// 조항 원문에서 "제N조(제목)" 표제를 뽑아 카드·상세 제목으로 쓴다.
// 위험 유형(risk_type)만 제목으로 쓰면 안전 조항이 전부 "표준 조항"으로 떠서
// 사용자가 올린 조항 중 어느 것인지 구분할 수 없다 — 원문 표제를 제목으로,
// 유형은 괄호 보조 표기로 내린다. 표제가 없는 원문은 앞부분을 잘라 보여준다.

const HEADING =
  /^\s*(제\s*\d+\s*조(?:의\s*\d+)?)\s*(?:\(([^)\n]{1,30})\)|【([^】\n]{1,30})】|\[([^\]\n]{1,30})\])?/

export function clauseHeading(originalText: string | null | undefined): string | null {
  if (!originalText) return null
  const m = HEADING.exec(originalText)
  if (m) {
    const num = m[1].replace(/\s+/g, '')
    const title = (m[2] ?? m[3] ?? m[4])?.trim()
    return title ? `${num}(${title})` : num
  }
  const snippet = originalText.trim().replace(/\s+/g, ' ')
  if (!snippet) return null
  return snippet.length > 18 ? `${snippet.slice(0, 18)}…` : snippet
}
