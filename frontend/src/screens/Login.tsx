import { useState } from 'react'
import { Button, Card, PageTitle } from '../components/ui'
import { signIn, signUp, type Session } from '../auth'
import { isCryptoAvailable } from '../crypto'
import { t, type LangCode } from '../i18n'

/** 로그인 / 회원가입 (#102).
 *
 * 로그인이 여는 기능은 "분석 결과를 계정에 보관하기" 하나뿐이다 — 계약서
 * 분석·교육·챗봇은 로그인 없이 그대로 쓸 수 있다(팀 결정 08-21).
 * 비밀번호는 서버로 가지 않고, 기기에서 파생한 인증 증명만 전송된다.
 */
export function LoginScreen({
  language = 'ko',
  onDone,
}: {
  language?: LangCode
  onDone: (session: Session) => void
}) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    if (busy) return
    setError(null)
    if (password.length < 8) {
      setError(t(language, 'lgErrWeak'))
      return
    }
    setBusy(true)
    try {
      const session = mode === 'signup' ? await signUp(email, password) : await signIn(email, password)
      onDone(session)
    } catch (err) {
      // auth.ts는 상태 코드만 올린다 — 문구는 여기서 현지화
      const code = err instanceof Error ? err.message : ''
      setError(
        t(
          language,
          code === '409' ? 'lgErrDup' : code === '401' ? 'lgErrCreds'
            : code === '429' ? 'lgErrRate' : 'lgErrNetwork',
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  const tab = (id: 'login' | 'signup', labelKey: 'lgTabLogin' | 'lgTabSignup') => (
    <button
      type="button"
      role="tab"
      aria-selected={mode === id}
      onClick={() => {
        setMode(id)
        setError(null)
      }}
      className={`flex-1 rounded-xl py-2.5 text-[14px] font-bold transition-colors ${
        mode === id ? 'bg-white text-ink-900 shadow-card' : 'text-ink-600 hover:text-ink-900'
      }`}
    >
      {t(language, labelKey)}
    </button>
  )

  const field = (
    labelKey: 'lgEmail' | 'lgPassword',
    type: 'email' | 'password',
    value: string,
    onChange: (v: string) => void,
    hint?: string,
  ) => (
    <label className="mt-4 block">
      <span className="text-[13px] font-semibold text-ink-600">{t(language, labelKey)}</span>
      <input
        type={type}
        value={value}
        autoComplete={type === 'email' ? 'email' : mode === 'signup' ? 'new-password' : 'current-password'}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && submit()}
        className="mt-1.5 w-full rounded-xl border border-ink-100 bg-white px-3.5 py-2.5 text-[15px] text-ink-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-50"
      />
      {hint && <span className="mt-1 block text-[12px] text-ink-400">{hint}</span>}
    </label>
  )

  return (
    <div className="mx-auto max-w-md animate-fade-up px-6 py-12 md:py-16">
      <PageTitle title={t(language, 'lgTitle')} desc={t(language, 'lgDesc')} />

      <Card className="mt-8 p-6">
        <div role="tablist" className="flex gap-1 rounded-2xl bg-ink-25 p-1">
          {tab('login', 'lgTabLogin')}
          {tab('signup', 'lgTabSignup')}
        </div>

        {field('lgEmail', 'email', email, setEmail)}
        {field('lgPassword', 'password', password, setPassword, t(language, 'lgPwHint'))}

        {error && (
          <p role="alert" className="mt-3 rounded-xl bg-danger-50 px-3.5 py-2.5 text-[13px] font-semibold text-danger-600">
            {error}
          </p>
        )}

        <Button full className="mt-5" onClick={submit} disabled={busy || !email || !password}>
          {t(language, 'lgSubmit')}
        </Button>

        {/* 영지식 설계 고지 — 가입 시에는 복구 불가 경고까지 함께 */}
        <p className="mt-4 text-[12px] leading-relaxed text-ink-400">{t(language, 'lgPrivacy')}</p>
        {mode === 'signup' && (
          <p className="mt-2 rounded-xl bg-caution-50 px-3.5 py-2.5 text-[12px] leading-relaxed text-caution-700">
            {t(language, 'lgWarnNoReset')}
          </p>
        )}
        {!isCryptoAvailable() && (
          <p role="alert" className="mt-2 text-[12px] font-semibold text-danger-600">
            {t(language, 'lgErrNetwork')}
          </p>
        )}
      </Card>
    </div>
  )
}
