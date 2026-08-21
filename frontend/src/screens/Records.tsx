import { useState } from 'react'
import { Button, Card, PageTitle } from '../components/ui'
import { deleteRecord, listRecords, type SavedRecord } from '../records'
import { domainLabel, t, type LangCode } from '../i18n'

/** 저장된 기록 목록 (#102 v1) — 옵트인 로컬 보관함 조회·재열람·삭제. */
export function RecordsScreen({
  language = 'ko',
  onOpen,
}: {
  language?: LangCode
  onOpen: (record: SavedRecord) => void
}) {
  const [records, setRecords] = useState<SavedRecord[]>(listRecords())

  return (
    <div className="mx-auto max-w-2xl animate-fade-up px-6 py-12 md:py-16">
      <PageTitle title={t(language, 'rcTitle')} desc={t(language, 'rcNote')} />

      {records.length === 0 ? (
        <Card className="mt-8 px-6 py-10 text-center text-[14px] leading-relaxed text-ink-400">
          {t(language, 'rcEmpty')}
        </Card>
      ) : (
        <div className="mt-8 space-y-3">
          {records.map((record) => (
            <Card key={record.id} className="flex flex-wrap items-center justify-between gap-3 p-5">
              <div className="min-w-0">
                <p className="text-[14px] font-bold text-ink-900">
                  {record.domain ? domainLabel(language, record.domain) : '—'}
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
                    setRecords(listRecords())
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
