import { useEffect, useRef, useState, type ReactNode } from 'react'

/** 스크롤 진입 시 나타나는 래퍼 (#134 모션).
 *
 * IntersectionObserver로 뷰포트 진입을 감지해 .is-visible을 붙인다.
 * 숨김 상태(opacity 0)는 index.css에서 prefers-reduced-motion:
 * no-preference일 때만 적용 — 움직임 최소화 사용자와 IO 미지원 환경은
 * 처음부터 보이는 상태라 콘텐츠가 사라질 위험이 없다.
 */
export function Reveal({
  children,
  delay = 0,
  className = '',
}: {
  children: ReactNode
  delay?: number // ms — 카드 그리드 스태거용
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(
    typeof IntersectionObserver === 'undefined',
  )

  useEffect(() => {
    const el = ref.current
    if (!el || visible) return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          io.disconnect()
        }
      },
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [visible])

  return (
    <div
      ref={ref}
      className={`reveal ${visible ? 'is-visible' : ''} ${className}`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  )
}
