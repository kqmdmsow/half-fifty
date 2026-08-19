/** 음성 안내(TTS) 유틸 — 선택 언어에 맞는 기기 최적 보이스를 골라 쓴다 (#86).
 *
 * Web Speech API의 기본 보이스는 기계음이 심한 경우가 많다. 같은 API 안에서도
 * 플랫폼별로 품질 좋은 보이스가 있어 우선순위로 선택한다 (한국어 기준):
 * - macOS: Yuna (시스템 프리미엄 한국어)
 * - Chrome: Google 한국어 (온라인 신경망 보이스)
 * - Windows: Heami / SunHi
 * 그 외 언어는 언어 코드가 일치하는 보이스 중 온라인(localService=false)
 * 신경망 계열을 우선한다. 일치 보이스가 없으면 utterance.lang만 지정해
 * 엔진 기본 처리에 맡긴다 (기기에 해당 언어 팩이 없는 경우).
 * 클라우드 TTS(Clova·ElevenLabs 등)는 비용·백엔드 프록시가 필요해 로드맵으로 남긴다.
 */

import type { LangCode } from './i18n'

// 앱 언어 코드 → BCP-47 (SpeechSynthesis lang)
const TTS_LANG: Record<LangCode, string> = {
  ko: 'ko-KR', en: 'en-US', zh: 'zh-CN', vi: 'vi-VN', th: 'th-TH', id: 'id-ID',
  tl: 'fil-PH', ne: 'ne-NP', km: 'km-KH', my: 'my-MM', mn: 'mn-MN', uz: 'uz-UZ',
  si: 'si-LK', bn: 'bn-BD', ru: 'ru-RU', ja: 'ja-JP',
}

// 한국어만 이름 우선순위가 검증돼 있다 — 그 외 언어는 온라인 보이스 우선 규칙만
const KO_VOICE_PRIORITY = ['yuna', 'google 한국어', 'google korean', 'sunhi', 'heami']

const cachedVoice = new Map<string, SpeechSynthesisVoice | null>()

function pickVoice(lang: string): SpeechSynthesisVoice | null {
  if (cachedVoice.has(lang)) return cachedVoice.get(lang) ?? null
  const prefix = lang.split('-')[0].toLowerCase()
  const voices = window.speechSynthesis.getVoices()
  const matching = voices.filter((v) =>
    v.lang.replace('_', '-').toLowerCase().startsWith(prefix),
  )
  let picked: SpeechSynthesisVoice | null = null
  if (matching.length) {
    if (prefix === 'ko') {
      for (const name of KO_VOICE_PRIORITY) {
        picked = matching.find((v) => v.name.toLowerCase().includes(name)) ?? null
        if (picked) break
      }
    }
    picked = picked ?? matching.find((v) => !v.localService) ?? matching[0]
  }
  cachedVoice.set(lang, picked)
  return picked
}

export function speak(text: string, language: LangCode = 'ko') {
  if (!('speechSynthesis' in window)) return
  const lang = TTS_LANG[language] ?? 'ko-KR'
  const utter = () => {
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = lang
    utterance.rate = 0.95
    const voice = pickVoice(lang)
    if (voice) utterance.voice = voice
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utterance)
  }
  // 보이스 목록은 비동기 로드된다 — 아직 비어 있으면 로드 완료 후 1회 재시도.
  if (window.speechSynthesis.getVoices().length === 0) {
    window.speechSynthesis.addEventListener('voiceschanged', utter, { once: true })
    return
  }
  utter()
}

export function stopSpeaking() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}
