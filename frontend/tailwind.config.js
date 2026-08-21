/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Pretendard GOV',
          'Pretendard Variable',
          'Pretendard',
          '-apple-system',
          'BlinkMacSystemFont',
          'system-ui',
          'Roboto',
          'Helvetica Neue',
          'Segoe UI',
          'Apple SD Gothic Neo',
          'Noto Sans KR',
          'sans-serif',
        ],
      },
      // KRDS 토큰 매핑 — 클래스명은 유지, 값은 src/index.css의 CSS 변수
      // (RGB 트리플릿)를 참조한다. 실값·KRDS 출처 토큰명은 index.css 주석 참조.
      // white까지 변수인 이유: KRDS 고대비 모드는 배경 반전(흰→검)이라
      // 변수 스왑만으로 모드가 전환되려면 white도 슬롯이어야 한다.
      colors: {
        white: 'rgb(var(--c-white) / <alpha-value>)',
        brand: {
          50: 'rgb(var(--c-brand-50) / <alpha-value>)',
          100: 'rgb(var(--c-brand-100) / <alpha-value>)',
          500: 'rgb(var(--c-brand-500) / <alpha-value>)',
          600: 'rgb(var(--c-brand-600) / <alpha-value>)',
          700: 'rgb(var(--c-brand-700) / <alpha-value>)',
        },
        ink: {
          900: 'rgb(var(--c-ink-900) / <alpha-value>)',
          700: 'rgb(var(--c-ink-700) / <alpha-value>)',
          600: 'rgb(var(--c-ink-600) / <alpha-value>)',
          400: 'rgb(var(--c-ink-400) / <alpha-value>)',
          300: 'rgb(var(--c-ink-300) / <alpha-value>)',
          200: 'rgb(var(--c-ink-200) / <alpha-value>)',
          100: 'rgb(var(--c-ink-100) / <alpha-value>)',
          50: 'rgb(var(--c-ink-50) / <alpha-value>)',
          25: 'rgb(var(--c-ink-25) / <alpha-value>)',
        },
        danger: {
          50: 'rgb(var(--c-danger-50) / <alpha-value>)',
          500: 'rgb(var(--c-danger-500) / <alpha-value>)',
          600: 'rgb(var(--c-danger-600) / <alpha-value>)',
        },
        caution: {
          50: 'rgb(var(--c-caution-50) / <alpha-value>)',
          500: 'rgb(var(--c-caution-500) / <alpha-value>)',
          700: 'rgb(var(--c-caution-700) / <alpha-value>)',
        },
        safe: {
          50: 'rgb(var(--c-safe-50) / <alpha-value>)',
          500: 'rgb(var(--c-safe-500) / <alpha-value>)',
          700: 'rgb(var(--c-safe-700) / <alpha-value>)',
        },
      },
      boxShadow: {
        // 기하는 기존 유지, 색만 KRDS alpha-shadow1/2/3 토큰
        card: '0 1px 3px var(--c-shadow-1), 0 6px 20px var(--c-shadow-2)',
        float: '0 8px 30px var(--c-shadow-3)',
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.45s cubic-bezier(0.16, 1, 0.3, 1) both',
        shimmer: 'shimmer 1.6s linear infinite',
      },
    },
  },
  plugins: [],
}
