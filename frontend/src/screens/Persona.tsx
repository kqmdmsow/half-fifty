import type { Language, Persona } from '../api'
import { Button, Card, PageTitle, Switch } from '../components/ui'
import { LANGUAGES, t } from '../i18n'

// 라벨·설명은 i18n(UI_PERSONA)에서 — 이 화면만 하드코딩 한국어로 남아 있었다
const PERSONAS: Array<{ id: Persona; emoji: string; titleKey: 'psAdult' | 'psSenior' | 'psForeigner'; descKey: 'psAdultDesc' | 'psSeniorDesc' | 'psForeignerDesc' }> = [
  { id: 'adult', emoji: '🙂', titleKey: 'psAdult', descKey: 'psAdultDesc' },
  { id: 'senior', emoji: '👵', titleKey: 'psSenior', descKey: 'psSeniorDesc' },
  { id: 'foreigner', emoji: '🌏', titleKey: 'psForeigner', descKey: 'psForeignerDesc' },
]

// 언어 목록은 i18n.ts에서 관리 (2025 체류외국인·E-9·유학생 통계 기반 16종)

export function PersonaScreen({
  persona,
  language,
  largeText,
  highContrast,
  voiceGuide,
  onPersonaChange,
  onLanguageChange,
  onToggleLargeText,
  onToggleHighContrast,
  onToggleVoiceGuide,
  onPrev,
  onStartAnalysis,
}: {
  persona: Persona
  language: Language
  largeText: boolean
  highContrast: boolean
  voiceGuide: boolean
  onPersonaChange: (persona: Persona) => void
  onLanguageChange: (language: Language) => void
  onToggleLargeText: () => void
  onToggleHighContrast: () => void
  onToggleVoiceGuide: () => void
  onPrev: () => void
  onStartAnalysis: () => void
}) {
  return (
    <div className="mx-auto max-w-xl animate-fade-up px-6 py-12 md:py-16">
      <PageTitle title={t(language, 'psTitle')} desc={t(language, 'psDesc')} />

      <div className="mt-8 grid gap-3 md:grid-cols-3">
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
              <p className="mt-4 text-[17px] font-bold text-ink-900">{t(language, item.titleKey)}</p>
              <p className="mt-1.5 text-[14px] leading-relaxed text-ink-400">{t(language, item.descKey)}</p>
            </button>
          )
        })}
      </div>

      {persona === 'foreigner' && (
        <Card className="mt-5 p-5">
          <p className="text-[13px] font-bold text-ink-400">{t(language, 'psLangLabel')}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {LANGUAGES.map((item) => {
              const active = language === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={active}
                  onClick={() => onLanguageChange(item.id)}
                  className={`rounded-full px-4 py-2 text-[14px] font-bold transition-colors ${
                    active
                      ? 'bg-brand-500 text-white'
                      : 'bg-ink-50 text-ink-600 hover:bg-ink-100'
                  }`}
                >
                  {item.label}
                </button>
              )
            })}
          </div>
          <p className="mt-3 text-[12px] leading-relaxed text-ink-400">
            {t(language, 'psLangHint')}
          </p>
        </Card>
      )}

      <Card className="mt-5 px-2 py-2">
        <p className="px-4 pb-1 pt-3 text-[13px] font-bold text-ink-400">{t(language, 'psA11y')}</p>
        <Switch
          checked={largeText}
          label={t(language, 'psLarge')}
          description={t(language, 'psLargeDesc')}
          onChange={onToggleLargeText}
        />
        <Switch
          checked={highContrast}
          label={t(language, 'psContrast')}
          description={t(language, 'psContrastDesc')}
          onChange={onToggleHighContrast}
        />
        <Switch
          checked={voiceGuide}
          label={t(language, 'psVoice')}
          description={t(language, 'psVoiceDesc')}
          onChange={onToggleVoiceGuide}
        />
      </Card>

      <div className="mt-8 flex gap-2.5">
        <Button variant="secondary" size="lg" onClick={onPrev}>
          {t(language, 'psPrev')}
        </Button>
        <Button size="lg" full onClick={onStartAnalysis}>
          {t(language, 'psStart')}
        </Button>
      </div>
    </div>
  )
}
