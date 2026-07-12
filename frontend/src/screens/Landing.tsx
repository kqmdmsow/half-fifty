import { Button, RiskBadge } from '../components/ui'

export function LandingScreen({ onStart }: { onStart: () => void }) {
  return (
    <div className="animate-fade-up">
      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-14 px-6 pb-24 pt-16 md:pt-24 lg:grid-cols-2">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3.5 py-1.5 text-[13px] font-bold text-brand-600">
            계약 전에, 한 번 더 안전하게
          </span>
          <h1 className="mt-6 text-[38px] font-bold leading-[1.25] tracking-[-0.02em] text-ink-900 md:text-[52px]">
            어려운 계약서,
            <br />
            쉬운 말로 확인하세요
          </h1>
          <p className="mt-5 max-w-md text-[17px] leading-relaxed text-ink-600">
            불리할 수 있는 조항과 그 근거를 찾아,
            <br className="hidden md:block" />
            계약 전에 꼭 물어볼 질문까지 알려드려요.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Button size="lg" onClick={onStart}>
              계약서 분석 시작하기
            </Button>
            <span className="text-[13px] font-medium text-ink-400">
              회원가입 없이 · 분석 후 원본 즉시 삭제
            </span>
          </div>
        </div>

        {/* 미리보기 목업 */}
        <div className="relative mx-auto w-full max-w-md">
          <div className="rounded-3xl border border-ink-100 bg-white p-7 shadow-card">
            <p className="text-[13px] font-bold text-ink-400">전세계약서.pdf</p>
            <div className="mt-4 space-y-2.5">
              <div className="h-2.5 w-3/5 rounded-full bg-ink-50" />
              <div className="h-2.5 w-full rounded-full bg-ink-50" />
              <div className="h-2.5 w-4/5 rounded-full bg-ink-50" />
              <div className="h-2.5 w-11/12 rounded-full bg-ink-50" />
            </div>
            <div className="mt-6 rounded-2xl bg-danger-50 p-4">
              <RiskBadge level="위험" />
              <p className="mt-2.5 text-[14px] font-semibold leading-relaxed text-ink-900">
                "계약 종료 후 3개월 이내에 보증금을 반환할 수 있다."
              </p>
            </div>
          </div>
          <div className="absolute -bottom-8 -right-3 w-72 rounded-2xl border border-ink-100 bg-white p-5 shadow-float md:-right-8">
            <p className="text-[13px] font-bold text-danger-500">보증금 반환 지연</p>
            <p className="mt-1.5 text-[16px] font-bold text-ink-900">
              보증금을 바로 받지 못할 수 있어요
            </p>
            <p className="mt-1.5 text-[13px] leading-relaxed text-ink-400">
              계약 종료일에 전액 반환 가능한지 상대방에게 확인해 보세요.
            </p>
          </div>
        </div>
      </section>

      {/* 기능 소개 */}
      <section className="border-t border-ink-50 bg-ink-25 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-center text-[26px] font-bold tracking-[-0.02em] text-ink-900 md:text-[32px]">
            계약서를 다 읽지 않아도
            <br />
            중요한 것만 정확하게
          </h2>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            <Feature
              emoji="💬"
              title="눈높이 맞춤 설명"
              body="일반 성인과 고령층, 읽는 사람에게 맞는 말투와 표현으로 조항을 풀어드려요."
            />
            <Feature
              emoji="🔍"
              title="위험 조항과 원문 근거"
              body="왜 불리한지 판단의 근거가 되는 원문을 함께 보여드려요."
            />
            <Feature
              emoji="✅"
              title="확인할 질문 제공"
              body="계약 상대방에게 바로 물어볼 수 있는 질문을 만들어드려요."
            />
          </div>
        </div>
      </section>

      {/* 이용 방법 */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-center text-[26px] font-bold tracking-[-0.02em] text-ink-900 md:text-[32px]">
            3분이면 충분해요
          </h2>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            <Step no="1" title="계약서 올리기" body="PDF를 올리거나 내용을 붙여넣으세요." />
            <Step no="2" title="AI 분석" body="조항별로 위험 신호를 찾고 근거를 정리해요." />
            <Step no="3" title="질문 준비" body="확인할 질문을 복사해 상대방에게 물어보세요." />
          </div>
        </div>
      </section>

      {/* 신뢰 */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <div className="rounded-3xl bg-ink-900 px-8 py-12 text-center md:px-16">
          <h2 className="text-[24px] font-bold text-white md:text-[28px]">
            개인정보는 걱정하지 마세요
          </h2>
          <p className="mx-auto mt-3.5 max-w-lg text-[15px] leading-relaxed text-ink-300">
            올려주신 계약서는 분석에만 사용하고 완료 즉시 서버에서 삭제해요. AI 학습에도 사용하지
            않아요.
          </p>
          <Button size="lg" className="mt-8 !bg-white !text-ink-900 hover:!bg-ink-50" onClick={onStart}>
            지금 무료로 분석하기
          </Button>
        </div>
      </section>

      {/* 푸터 */}
      <footer className="border-t border-ink-50 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-[13px] text-ink-400 md:flex-row">
          <span className="font-semibold">© 하프피프티</span>
          <span className="max-w-md text-center leading-relaxed md:text-right">
            본 서비스의 분석 결과는 참고용 정보이며 법률 자문이 아닙니다. 중요한 계약은 전문가와
            상담하세요.
          </span>
        </div>
      </footer>
    </div>
  )
}

function Feature({ emoji, title, body }: { emoji: string; title: string; body: string }) {
  return (
    <div className="rounded-3xl bg-white p-7 shadow-card">
      <span className="text-[28px]">{emoji}</span>
      <p className="mt-4 text-[17px] font-bold text-ink-900">{title}</p>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-400">{body}</p>
    </div>
  )
}

function Step({ no, title, body }: { no: string; title: string; body: string }) {
  return (
    <div className="rounded-3xl border border-ink-100 p-7">
      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 text-[15px] font-extrabold text-brand-600">
        {no}
      </span>
      <p className="mt-4 text-[17px] font-bold text-ink-900">{title}</p>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-400">{body}</p>
    </div>
  )
}
