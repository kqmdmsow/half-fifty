/**
 * 판정 근거를 원문에서 하이라이트한다 (#174).
 *
 * 사용자가 판정을 검증하려면 근거가 원문 어느 대목인지 눈으로 짚을 수 있어야
 * 한다. "AI가 그렇다니까 그런가 보다"에서 "여기 이 문장 때문에 위험하구나"로
 * 넘어가는 차이다.
 *
 * 구간은 백엔드가 계산해 내려준다(citation_check.locate_quotes) — 프론트에서
 * 문자열 검색으로 다시 찾으면 공백·표기 차이 때문에 어긋나고, 무엇보다
 * "근거가 원문에 실재하는가"를 두 곳에서 다르게 판단하게 된다.
 */
export function HighlightedText({
  text,
  spans = [],
  className = '',
}: {
  text: string
  spans?: number[][]
  className?: string
}) {
  // 구간이 없거나 범위를 벗어나면 그냥 원문을 낸다 — 하이라이트는 부가 기능이고
  // 원문 표시가 실패하면 안 된다.
  const valid = spans
    .filter(([s, e]) => Number.isInteger(s) && Number.isInteger(e) && 0 <= s && s < e && e <= text.length)
    .sort((a, b) => a[0] - b[0])
  if (valid.length === 0) return <span className={className}>{text}</span>

  const parts: React.ReactNode[] = []
  let cursor = 0
  valid.forEach(([start, end], i) => {
    if (start < cursor) return // 겹침 방어 (백엔드가 병합하지만 이중 안전)
    if (start > cursor) parts.push(text.slice(cursor, start))
    parts.push(
      <mark key={i} className="rounded bg-caution-50 px-0.5 font-semibold text-ink-900">
        {text.slice(start, end)}
      </mark>,
    )
    cursor = end
  })
  if (cursor < text.length) parts.push(text.slice(cursor))
  return <span className={className}>{parts}</span>
}
