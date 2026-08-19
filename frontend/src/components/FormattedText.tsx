// LLM 설명이 한 덩어리 문단으로 와서 읽기 어렵다는 사용자 피드백 반영 —
// 문장 단위로 줄을 나누고, "(1) … (2) …" 열거는 번호 목록으로, 첫 문장(핵심
// 요지)은 lead 옵션으로 볼드 처리한다. 텍스트 내용은 건드리지 않는다.

const ENUM_MARKER = /\((\d{1,2})\)\s*/g
// 한국어 종결(다./요.) 뒤 공백에서 문장을 나눈다 — "1.5%" 같은 숫자 소수점은
// 뒤에 공백이 없어 분리되지 않는다.
const SENTENCE_END = /(?<=[.!?…])\s+/

function splitSentences(text: string): string[] {
  return text
    .split(SENTENCE_END)
    .map((s) => s.trim())
    .filter(Boolean)
}

function splitEnumeration(text: string): { intro: string; items: string[] } {
  const markers = [...text.matchAll(ENUM_MARKER)]
  if (markers.length < 2) return { intro: text, items: [] }
  const first = markers[0].index ?? 0
  const intro = text.slice(0, first).trim()
  const items: string[] = []
  markers.forEach((m, i) => {
    const start = (m.index ?? 0) + m[0].length
    const end = i + 1 < markers.length ? markers[i + 1].index : text.length
    const item = text.slice(start, end).trim().replace(/[,、]\s*$/, '')
    if (item) items.push(item)
  })
  return { intro, items }
}

export function FormattedText({
  text,
  lead = false,
  className = '',
}: {
  text: string
  /** 첫 문장을 핵심 요지로 볼드 처리 */
  lead?: boolean
  className?: string
}) {
  const { intro, items } = splitEnumeration(text)
  const sentences = splitSentences(intro)

  return (
    <div className={className}>
      {sentences.map((sentence, i) => (
        <p
          key={i}
          className={`leading-relaxed ${i > 0 ? 'mt-1.5' : ''} ${
            lead && i === 0 ? 'font-bold text-ink-900' : ''
          }`}
        >
          {sentence}
        </p>
      ))}
      {items.length > 0 && (
        <ol className="mt-2.5 space-y-1.5">
          {items.map((item, i) => (
            <li key={i} className="flex gap-2 leading-relaxed">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-ink-900/5 text-[12px] font-bold">
                {i + 1}
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
