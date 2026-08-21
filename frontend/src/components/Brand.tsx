/** 브랜드 마크·워드마크 (#134).
 *
 * 로고 원본: ~/Downloads/조목조목-로고 (2안 — 은유를 하나로 줄인 방향).
 * 규격서 그대로 옮긴다: 그리드 48×48, 본체 획 4.5 / 조항 줄 3.5~4,
 * 남색 #14264F(본체) + 파랑 #1E5FE0(짚어낸 조항). 늘이거나 획 굵기를
 * 바꾸지 말 것 — 크기는 width/height로만 조절한다.
 */

const NAVY = '#14264F'
const BLUE = '#1E5FE0'

/** 문서 접힘 마크 — "여기 다시 봐야 함". 헤더·파비콘의 주 마크. */
export function DocMark({ size = 28, className = '' }: { size?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      width={size}
      height={size}
      fill="none"
      aria-hidden
      className={className}
    >
      <g stroke={NAVY} strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9.5 6.5H26.5L39.5 19.5V41.5H9.5Z" />
        <path d="M26.5 6.5V19.5H39.5" />
        <path d="M15.5 28H31" strokeWidth="3.5" />
      </g>
      <path d="M15.5 35.5H27" stroke={BLUE} strokeWidth="4" strokeLinecap="round" />
    </svg>
  )
}

/** 돋보기 마크 — 렌즈 안에 조항 두 줄. 조항을 들여다보는 중(분석 화면). */
export function LensMark({ size = 44, className = '' }: { size?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      width={size}
      height={size}
      fill="none"
      aria-hidden
      className={className}
    >
      <g stroke={NAVY} strokeLinecap="round" strokeLinejoin="round">
        <circle cx="20" cy="20" r="14" strokeWidth="5" />
        <path d="M30.5 30.5L43 43" strokeWidth="5.5" />
        <path d="M13.5 16H27" strokeWidth="4" />
      </g>
      <path d="M13.5 24.5H23.5" stroke={BLUE} strokeWidth="4" strokeLinecap="round" />
    </svg>
  )
}

/** 워드마크 — '목' 음절에 파랑 포인트를 준다(로고 시안의 2톤을 글자로 옮김).
 *  글리프 일부만 색을 넣는 것은 웹폰트로 불가능해 음절 단위로 나눈다. */
export function Wordmark({ className = '' }: { className?: string }) {
  return (
    <span className={`font-bold tracking-tight ${className}`} style={{ color: NAVY }}>
      조<span style={{ color: BLUE }}>목</span>조<span style={{ color: BLUE }}>목</span>
    </span>
  )
}
