/** 앱 내 음성 명령 (#127) — Web Speech API(SpeechRecognition), ko 우선.
 *
 * OS 음성 제어(맥 음성 제어·Voice Access)는 시맨틱 버튼(#123)으로 이미
 * 호환된다 — 이 모듈은 그 위의 '+α': 마이크 버튼 하나로 "다음 조항",
 * "읽어줘" 같은 짧은 명령을 처리한다. 지원 브라우저(Chrome 계열)가
 * 아니면 isVoiceSupported()가 false를 반환하고 UI가 버튼을 숨긴다.
 *
 * 명령은 포함 매칭(정확 발화 요구 않음): "다음 조항으로 가줘"도 '다음' 매칭.
 * 인식 결과는 어디에도 전송·저장하지 않는다 (명령 해석 후 즉시 폐기).
 */

export type VoiceCommand =
  | 'next'      // 다음 조항
  | 'prev'      // 이전 조항
  | 'read'      // 읽어줘 (현재 조항/전체)
  | 'stop'      // 멈춰
  | 'summary'   // 요약으로
  | 'easier'    // 더 쉽게

const PATTERNS: Array<[VoiceCommand, RegExp]> = [
  ['next', /다음|넘겨/],
  ['prev', /이전|뒤로/],
  ['read', /읽어|낭독|들려/],
  ['stop', /멈춰|중지|그만/],
  ['summary', /요약|목록|처음/],
  ['easier', /쉽게|간단하게/],
]

type SpeechRecognitionCtor = new () => any

function getRecognition(): SpeechRecognitionCtor | null {
  const w = window as any
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

export function isVoiceSupported(): boolean {
  return getRecognition() !== null
}

export interface VoiceSession {
  stop: () => void
}

/** 연속 인식 세션 시작 — 명령 매칭 시 onCommand, 상태 변화 시 onState. */
export function startVoiceSession(
  onCommand: (cmd: VoiceCommand, transcript: string) => void,
  onState: (listening: boolean) => void,
): VoiceSession | null {
  const Ctor = getRecognition()
  if (!Ctor) return null
  const rec = new Ctor()
  rec.lang = 'ko-KR'
  rec.continuous = true
  rec.interimResults = false
  let active = true

  rec.onresult = (event: any) => {
    const transcript: string = event.results[event.results.length - 1][0].transcript
    for (const [cmd, pattern] of PATTERNS) {
      if (pattern.test(transcript)) {
        onCommand(cmd, transcript)
        break
      }
    }
  }
  rec.onstart = () => onState(true)
  rec.onend = () => {
    // 브라우저가 세션을 임의 종료하면 활성 상태인 동안 재시작 (연속 청취)
    if (active) {
      try { rec.start() } catch { onState(false) }
    } else {
      onState(false)
    }
  }
  rec.onerror = (e: any) => {
    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
      active = false
      onState(false)
    }
  }
  try {
    rec.start()
  } catch {
    return null
  }
  return {
    stop: () => {
      active = false
      try { rec.stop() } catch { /* noop */ }
    },
  }
}
