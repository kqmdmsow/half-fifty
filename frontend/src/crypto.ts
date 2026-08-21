/** 영지식 기록 보관용 클라이언트 암호화 (#102).
 *
 * 서버는 계약 분석 결과를 **복호화할 수 없는 형태로만** 보관한다. 그래서
 * 로그인을 붙여도 "서버는 계약 내용을 갖지 않는다"는 제품 약속이 유지된다.
 *
 * 비밀번호 → PBKDF2(210k, SHA-256) → 64바이트를 둘로 쪼갠다:
 *   앞 32B = AES-GCM 암호화 키 (기기 밖으로 절대 나가지 않음)
 *   뒤 32B = 인증 증명(authProof, 서버 전송) — 서버는 여기에 BCrypt를 한 번 더
 *            씌워 저장하므로, DB가 통째로 유출돼도 암호화 키를 복원할 수 없다.
 *
 * salt는 이메일에서 결정적으로 만든다(SHA-256). 서버에 salt를 물어보는 왕복이
 * 없어 "가입 여부"가 새지 않는 대신, 무작위 salt보다는 약하다 — 계정별로는
 * 여전히 유일하므로 범용 레인보우 테이블에는 안전하다.
 *
 * 한계(정직하게): 비밀번호를 잊으면 서버도 우리도 기록을 되살릴 수 없다.
 * 가입 화면에서 이 점을 반드시 고지한다.
 */

const ITERATIONS = 210_000
const SALT_PREFIX = 'jomokjomok:v1:'

export interface DerivedKeys {
  /** 서버로 보내는 인증 증명 (base64) */
  authProof: string
  /** 기기에 남는 암호화 키 (raw base64 — 저장·복원용) */
  encKeyRaw: string
}

function toBase64(bytes: ArrayBuffer | Uint8Array): string {
  const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes)
  let binary = ''
  view.forEach((b) => {
    binary += String.fromCharCode(b)
  })
  return btoa(binary)
}

function fromBase64(value: string): Uint8Array {
  return Uint8Array.from(atob(value), (c) => c.charCodeAt(0))
}

/** WebCrypto의 BufferSource 인자에 넘길 ArrayBuffer로 복사한다 —
 *  TS 5.7의 Uint8Array<ArrayBufferLike> 제네릭과 BufferSource 불일치 회피. */
function bufferOf(view: Uint8Array): ArrayBuffer {
  return view.buffer.slice(view.byteOffset, view.byteOffset + view.byteLength) as ArrayBuffer
}

async function saltFor(email: string): Promise<ArrayBuffer> {
  const digest = await crypto.subtle.digest(
    'SHA-256',
    bufferOf(new TextEncoder().encode(SALT_PREFIX + email.trim().toLowerCase())),
  )
  return bufferOf(new Uint8Array(digest).slice(0, 16))
}

/** 비밀번호에서 인증 증명과 암호화 키를 파생한다 (네트워크 왕복 없음). */
export async function deriveKeys(email: string, password: string): Promise<DerivedKeys> {
  const material = await crypto.subtle.importKey(
    'raw',
    bufferOf(new TextEncoder().encode(password)),
    'PBKDF2',
    false,
    ['deriveBits'],
  )
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt: await saltFor(email), iterations: ITERATIONS, hash: 'SHA-256' },
    material,
    512,
  )
  const all = new Uint8Array(bits)
  return { encKeyRaw: toBase64(all.slice(0, 32)), authProof: toBase64(all.slice(32)) }
}

async function importKey(encKeyRaw: string): Promise<CryptoKey> {
  return crypto.subtle.importKey('raw', bufferOf(fromBase64(encKeyRaw)), 'AES-GCM', false, [
    'encrypt',
    'decrypt',
  ])
}

export interface Envelope {
  iv: string
  ciphertext: string
}

export async function encryptJson(encKeyRaw: string, value: unknown): Promise<Envelope> {
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const data = bufferOf(new TextEncoder().encode(JSON.stringify(value)))
  const cipher = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv: bufferOf(iv) },
    await importKey(encKeyRaw),
    data,
  )
  return { iv: toBase64(iv), ciphertext: toBase64(cipher) }
}

/** 복호화 실패(키 불일치·손상)는 null — 호출부가 해당 기록만 건너뛴다. */
export async function decryptJson<T>(encKeyRaw: string, envelope: Envelope): Promise<T | null> {
  try {
    const plain = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: bufferOf(fromBase64(envelope.iv)) },
      await importKey(encKeyRaw),
      bufferOf(fromBase64(envelope.ciphertext)),
    )
    return JSON.parse(new TextDecoder().decode(plain)) as T
  } catch {
    return null
  }
}

/** WebCrypto는 보안 컨텍스트(https·localhost)에서만 동작한다. */
export function isCryptoAvailable(): boolean {
  return typeof crypto !== 'undefined' && !!crypto.subtle
}
