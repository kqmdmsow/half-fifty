/** 음성 안내(TTS) 유틸 — 기기에서 가장 자연스러운 한국어 보이스를 골라 쓴다.
 *
 * Web Speech API의 기본 보이스는 기계음이 심한 경우가 많다. 같은 API 안에서도
 * 플랫폼별로 품질 좋은 보이스가 있어 우선순위로 선택한다:
 * - macOS: Yuna (시스템 프리미엄 한국어)
 * - Chrome: Google 한국어 (온라인 신경망 보이스)
 * - Windows: Heami / SunHi
 * 그 외에는 온라인(localService=false) 보이스를 우선한다 — 대체로 신경망 계열.
 * 클라우드 TTS(Clova·ElevenLabs 등)는 비용·백엔드 프록시가 필요해 로드맵으로 남긴다.
 */

const VOICE_PRIORITY = ['yuna', 'google 한국어', 'google korean', 'sunhi', 'heami']

let cachedVoice: SpeechSynthesisVoice | null = null

function pickKoreanVoice(): SpeechSynthesisVoice | null {
  if (cachedVoice) return cachedVoice
  const voices = window.speechSynthesis.getVoices()
  const korean = voices.filter((v) => v.lang.replace('_', '-').toLowerCase().startsWith('ko'))
  if (!korean.length) return null
  for (const name of VOICE_PRIORITY) {
    const hit = korean.find((v) => v.name.toLowerCase().includes(name))
    if (hit) {
      cachedVoice = hit
      return hit
    }
  }
  cachedVoice = korean.find((v) => !v.localService) ?? korean[0]
  return cachedVoice
}

export function speak(text: string) {
  if (!('speechSynthesis' in window)) return
  const utter = () => {
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'ko-KR'
    utterance.rate = 0.95
    const voice = pickKoreanVoice()
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
