import { useEffect, useState } from 'react'

/** 히어로 회전 헤드라인 (#134) — '쉬운'을 축으로 좌우 단어가 계속 바뀐다.
 *
 * imweb 스타일 레퍼런스(팀 피드백). 한국어 조어("~하기 쉬운 ~") 구조라
 * ko 전용이고, 다른 언어는 기존 정적 타이틀을 유지한다(Landing.tsx 분기).
 * 움직임 최소화 설정이면 인터벌을 걸지 않아 첫 문구로 고정된다.
 */
const PAIRS: Array<[string, string]> = [
  ['이해하기', '전세계약'],
  ['읽기', '대출약정'],
  ['알기', '근로계약'],
  ['확인하기', '보험약관'],
]

export function RotatingTitle() {
  const [idx, setIdx] = useState(0)

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const timer = setInterval(() => setIdx((i) => (i + 1) % PAIRS.length), 2600)
    return () => clearInterval(timer)
  }, [])

  const [left, right] = PAIRS[idx]
  return (
    <span aria-label="이해하기 쉬운 계약서">
      <span key={`l-${idx}`} aria-hidden className="word-swap">
        {left}
      </span>{' '}
      <span
        aria-hidden
        className="bg-[linear-gradient(transparent_60%,rgb(var(--c-brand-100))_60%)] px-1"
      >
        쉬운
      </span>
      <br className="md:hidden" />{' '}
      <span key={`r-${idx}`} aria-hidden className="word-swap text-brand-500">
        {right}
      </span>
    </span>
  )
}
