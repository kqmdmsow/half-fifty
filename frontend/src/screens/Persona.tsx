import type { Persona } from '../api'
import { Button, Card, PageTitle, Switch } from '../components/ui'

const PERSONAS: Array<{ id: Persona; emoji: string; title: string; desc: string }> = [
  {
    id: 'adult',
    emoji: '🙂',
    title: '일반 성인',
    desc: '법률 용어를 짧게 풀이하고 핵심을 간결하게 설명해요.',
  },
  {
    id: 'senior',
    emoji: '👵',
    title: '고령층',
    desc: '짧은 문장과 일상적인 표현, 익숙한 예시로 설명해요.',
  },
]

export function PersonaScreen({
  persona,
  largeText,
  highContrast,
  voiceGuide,
  onPersonaChange,
  onToggleLargeText,
  onToggleHighContrast,
  onToggleVoiceGuide,
  onPrev,
  onStartAnalysis,
}: {
  persona: Persona
  largeText: boolean
  highContrast: boolean
  voiceGuide: boolean
  onPersonaChange: (persona: Persona) => void
  onToggleLargeText: () => void
  onToggleHighContrast: () => void
  onToggleVoiceGuide: () => void
  onPrev: () => void
  onStartAnalysis: () => void
}) {
  return (
    <div className="mx-auto max-w-xl animate-fade-up px-6 py-12 md:py-16">
      <PageTitle
        title="누구에게 맞춰 설명할까요?"
        desc="위험 판단 기준은 동일해요. 설명의 말투와 쉬운 정도만 달라져요."
      />

      <div className="mt-8 grid gap-3 md:grid-cols-2">
        {PERSONAS.map((item) => {
          const active = persona === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onPersonaChange(item.id)}
              aria-pressed={active}
              className={`rounded-3xl border-2 bg-white p-6 text-left transition-all ${
                active
                  ? 'border-brand-500 shadow-card'
                  : 'border-ink-100 hover:border-ink-200'
              }`}
            >
              <div className="flex items-start justify-between">
                <span className="text-[28px]">{item.emoji}</span>
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-[13px] font-bold text-white transition-colors ${
                    active ? 'bg-brand-500' : 'bg-ink-100'
                  }`}
                >
                  ✓
                </span>
              </div>
              <p className="mt-4 text-[17px] font-bold text-ink-900">{item.title}</p>
              <p className="mt-1.5 text-[14px] leading-relaxed text-ink-400">{item.desc}</p>
            </button>
          )
        })}
      </div>

      <Card className="mt-5 px-2 py-2">
        <p className="px-4 pb-1 pt-3 text-[13px] font-bold text-ink-400">읽기 편한 화면 설정</p>
        <Switch
          checked={largeText}
          label="글자 크게 보기"
          description="전체 화면의 글자가 커져요"
          onChange={onToggleLargeText}
        />
        <Switch
          checked={highContrast}
          label="높은 명암 사용"
          description="흐린 글자를 더 진하게 보여줘요"
          onChange={onToggleHighContrast}
        />
        <Switch
          checked={voiceGuide}
          label="설명 음성으로 듣기"
          description="조항 설명을 소리로 들을 수 있어요"
          onChange={onToggleVoiceGuide}
        />
      </Card>

      <div className="mt-8 flex gap-2.5">
        <Button variant="secondary" size="lg" onClick={onPrev}>
          이전
        </Button>
        <Button size="lg" full onClick={onStartAnalysis}>
          계약서 분석 시작
        </Button>
      </div>
    </div>
  )
}
