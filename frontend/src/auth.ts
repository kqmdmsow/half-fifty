/** 로그인 세션 + 서버 기록 동기화 (#102).
 *
 * 저장하는 것: 토큰(30일)과 암호화 키를 한 덩어리로 localStorage에.
 * 로그아웃하면 둘 다 지운다. 키를 기기에 두는 이유는 재방문마다 비밀번호를
 * 다시 받지 않기 위함이고, 이 설계가 막는 것은 **서버 유출**이다(XSS까지
 * 막지는 못한다 — crypto.ts 주석 참조).
 */

import { decryptJson, deriveKeys, encryptJson, type Envelope } from './crypto'
import type { SavedRecord } from './records'

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8080'
const KEY = 'jmjm_auth'

export interface Session {
  email: string
  token: string
  encKeyRaw: string
}

export function currentSession(): Session | null {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

export function signOut() {
  localStorage.removeItem(KEY)
}

async function authRequest(
  path: 'signup' | 'login',
  email: string,
  password: string,
): Promise<Session> {
  const { authProof, encKeyRaw } = await deriveKeys(email, password)
  const res = await fetch(`${BASE_URL}/api/auth/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email.trim().toLowerCase(), authProof }),
  })
  if (!res.ok) {
    // 서버 메시지(한국어)를 그대로 쓰지 않고 상태 코드만 올려 화면에서 현지화한다
    throw new Error(String(res.status))
  }
  const data = (await res.json()) as { token: string; email: string }
  const session: Session = { email: data.email, token: data.token, encKeyRaw }
  localStorage.setItem(KEY, JSON.stringify(session))
  return session
}

export const signUp = (email: string, password: string) => authRequest('signup', email, password)
export const signIn = (email: string, password: string) => authRequest('login', email, password)

function authHeaders(session: Session) {
  return { Authorization: `Bearer ${session.token}`, 'Content-Type': 'application/json' }
}

/** 서버에 보관된 기록 — 복호화는 여기서, 서버는 암호문만 알고 있다. */
export async function fetchServerRecords(session: Session): Promise<SavedRecord[]> {
  const res = await fetch(`${BASE_URL}/api/records`, { headers: authHeaders(session) })
  if (res.status === 401 || res.status === 403) {
    signOut()
    throw new Error('401')
  }
  if (!res.ok) throw new Error(String(res.status))
  const rows = (await res.json()) as Array<Envelope & { id: string; savedAt: number }>
  const decrypted = await Promise.all(
    rows.map(async (row) => {
      const record = await decryptJson<SavedRecord>(session.encKeyRaw, row)
      // 복호화 실패(다른 비밀번호로 저장된 기록 등)는 목록에서 조용히 제외한다
      return record ? { ...record, id: row.id, savedAt: row.savedAt } : null
    }),
  )
  return decrypted.filter((r): r is SavedRecord => r !== null)
}

export async function pushServerRecord(session: Session, record: SavedRecord): Promise<void> {
  const envelope = await encryptJson(session.encKeyRaw, record)
  const res = await fetch(`${BASE_URL}/api/records/${encodeURIComponent(record.id)}`, {
    method: 'PUT',
    headers: authHeaders(session),
    body: JSON.stringify({ ...envelope, savedAt: record.savedAt }),
  })
  if (!res.ok) throw new Error(String(res.status))
}

export async function deleteServerRecord(session: Session, id: string): Promise<void> {
  await fetch(`${BASE_URL}/api/records/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: authHeaders(session),
  })
}

/** 탈퇴 — 서버의 계정·암호문을 지우고 기기 세션도 정리한다. */
export async function deleteAccount(session: Session): Promise<void> {
  await fetch(`${BASE_URL}/api/auth/me`, { method: 'DELETE', headers: authHeaders(session) })
  signOut()
}
