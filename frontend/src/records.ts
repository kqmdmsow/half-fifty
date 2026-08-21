/** 옵트인 로컬 기록 보관함 (#102 v1).
 *
 * '분석 후 즉시 삭제'는 서버 원칙이다 — 이 모듈은 **사용자가 명시적으로
 * 버튼을 눌렀을 때만** 자신의 기기(localStorage)에 결과를 남긴다. 서버로는
 * 아무것도 전송되지 않으므로 무저장 원칙과 충돌하지 않는다.
 *
 * 서버 로그인+계정 동기화는 Render Postgres 인프라 결정 후 별도 구현(#102).
 * 저장 상한 20건(초과 시 오래된 것부터 삭제) — localStorage 용량 보호.
 */

import type { AnalyzeResponse } from './api'

const KEY = 'jmjm_records'
const MAX_RECORDS = 20

export interface SavedRecord {
  id: string
  savedAt: number
  domain: string
  language: string
  clauseCount: number
  dangerCount: number
  data: AnalyzeResponse
}

function load(): SavedRecord[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '[]')
  } catch {
    return []
  }
}

function persist(records: SavedRecord[]) {
  localStorage.setItem(KEY, JSON.stringify(records.slice(0, MAX_RECORDS)))
}

export function listRecords(): SavedRecord[] {
  return load()
}

export function saveRecord(
  data: AnalyzeResponse,
  meta: { domain: string; language: string },
): SavedRecord {
  const record: SavedRecord = {
    id: `rec_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    savedAt: Date.now(),
    domain: meta.domain,
    language: meta.language,
    clauseCount: data.results.length,
    dangerCount: data.results.filter((r) => r.risk_level === '위험').length,
    data,
  }
  persist([record, ...load()])
  return record
}

export function deleteRecord(id: string) {
  persist(load().filter((r) => r.id !== id))
}
