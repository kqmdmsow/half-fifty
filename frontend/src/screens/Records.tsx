import { useEffect, useState } from 'react'
import { Button, Card, PageTitle } from '../components/ui'
import { deleteRecord, listRecords, type SavedRecord } from '../records'
import { deleteServerRecord, fetchServerRecords, type Session } from '../auth'
import { domainLabel, t, type LangCode } from '../i18n'

/** 저장된 기록 목록 (#102) — 기기 보관본 + (로그인 시) 계정 보관본.
 *
 * 계정 보관본은 서버에서 암호문으로 받아 이 화면에서 복호화한다 — 서버는
 * 목록에 뜨는 문서 유형·위험 건수조차 알지 못한다(auth.ts).
 */
export function RecordsScreen({
  language = 'ko',
  session = null,
  onOpen,
}: {
  language?: LangCode
  session?: Session | null
  onOpen: (record: SavedRecord) => void
}) {
  const [records, setRecords] = useState<SavedRecord[]>(listRecords())
  const [serverIds, setServerIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!session) {
      setServerIds(new Set())
      return
    }
    let alive = true
    fetchServerRecords(session)
      .then((remote) => {
        if (!alive) return
        setServerIds(new Set(remote.map((r) => r.id)))
        // 같은 id는 계정 보관본을 우선 — 기기 목록과 합쳐 최신순 정렬
        const local = listRecords().filter((r) => !remote.some((s) => s.id === r.id))
        setRecords([...remote, ...local].sort((a, b) => b.savedAt - a.savedAt))
      })
      .catch(() => {
        /* 서버 조회 실패 시 기기 보관본만 보여준다 */
      })
    return () => {
      alive = false
    }
  }, [session])

  return (
    <div className="mx-auto max-w-2xl animate-fade-up px-6 py-12 md:py-16">
      <PageTitle title={t(language, 'rcTitle')} desc={t(language, session ? 'rcNoteAccount' : 'rcNote')} />

      {records.length === 0 ? (
        <Card className="mt-8 px-6 py-10 text-center text-[14px] leading-relaxed text-ink-400">
          {t(language, 'rcEmpty')}
        </Card>
      ) : (
        <div className="mt-8 space-y-3">
          {records.map((record) => (
            <Card key={record.id} className="flex flex-wrap items-center justify-between gap-3 p-5">
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2 text-[14px] font-bold text-ink-900">
                  {record.domain ? domainLabel(language, record.domain) : '—'}
                  <span
                    className={`rounded-md px-1.5 py-0.5 text-[11px] font-bold ${
                      serverIds.has(record.id)
                        ? 'bg-brand-50 text-brand-600'
                        : 'bg-ink-50 text-ink-600'
                    }`}
                  >
                    {t(language, serverIds.has(record.id) ? 'rcFromServer' : 'rcFromDevice')}
                  </span>
                  <span className="ml-2 font-semibold text-ink-400">
                    {new Intl.DateTimeFormat(undefined, {
                      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                    }).format(record.savedAt)}
                  </span>
                </p>
                <p className="mt-0.5 text-[13px] text-ink-400">
                  {t(language, 'rcMeta', { n: record.dangerCount, total: record.clauseCount })}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button size="sm" onClick={() => onOpen(record)}>
                  {t(language, 'rcView')}
                </Button>
                <button
                  type="button"
                  onClick={() => {
                    deleteRecord(record.id)
                    // 계정 보관본이면 서버에서도 함께 지운다 (#102)
                    if (session && serverIds.has(record.id)) {
                      void deleteServerRecord(session, record.id)
                      setServerIds((prev) => {
                        const next = new Set(prev)
                        next.delete(record.id)
                        return next
                      })
                    }
                    setRecords((prev) => prev.filter((r) => r.id !== record.id))
                  }}
                  className="rounded-xl bg-danger-50 px-3.5 py-2 text-[13px] font-bold text-danger-600 transition-colors hover:bg-danger-100"
                >
                  {t(language, 'rcDelete')}
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
