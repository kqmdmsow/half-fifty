/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
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
      colors: {
        brand: {
          50: '#EBF3FE',
          100: '#D6E7FD',
          500: '#3182F6',
          600: '#1B64DA',
          700: '#1957C2',
        },
        ink: {
          900: '#191F28',
          700: '#333D4B',
          600: '#4E5968',
          400: '#8B95A1',
          300: '#B0B8C1',
          200: '#D1D6DB',
          100: '#E5E8EB',
          50: '#F2F4F6',
          25: '#F9FAFB',
        },
        danger: { 50: '#FEECEE', 500: '#F04452', 600: '#D22030' },
        caution: { 50: '#FFF3E0', 500: '#FE9800', 700: '#B65C00' },
        safe: { 50: '#E5F9F1', 500: '#00C471', 700: '#00794D' },
      },
      boxShadow: {
        card: '0 1px 3px rgba(25, 31, 40, 0.06), 0 6px 20px rgba(25, 31, 40, 0.05)',
        float: '0 8px 30px rgba(25, 31, 40, 0.12)',
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
