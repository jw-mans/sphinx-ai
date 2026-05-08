import { useState, FormEvent } from 'react'
import { login, register } from '../api/auth'
import type { TokenResponse } from '../api/auth'

interface Props {
  onSuccess: (resp: TokenResponse) => void
}

export function AuthPage({ onSuccess }: Props) {
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handle = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const resp =
        tab === 'login'
          ? await login(email, password)
          : await register(email, password, name)
      onSuccess(resp)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Что-то пошло не так')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 mb-4">
            <svg className="w-7 h-7 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.3 24.3 0 014.5 0m0 0v5.714a2.25 2.25 0 001.357 2.059l.524.22a1.5 1.5 0 001.03 0l.524-.22a2.25 2.25 0 001.357-2.059V3.104m-6.25 0c.25.023.501.05.75.082M12 21v-3.75m0 0a2.25 2.25 0 00-2.25-2.25H7.5M12 17.25a2.25 2.25 0 012.25-2.25H16.5" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Sphinx</h1>
          <p className="text-slate-500 text-sm mt-1">AI-симулятор технического интервью</p>
        </div>

        {/* Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
          {/* Tabs */}
          <div className="flex rounded-lg bg-slate-800/60 p-1 mb-6">
            {(['login', 'register'] as const).map(t => (
              <button
                key={t}
                onClick={() => { setTab(t); setError(null) }}
                className={`flex-1 py-2 rounded-md text-sm font-medium transition-all ${
                  tab === t
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {t === 'login' ? 'Войти' : 'Регистрация'}
              </button>
            ))}
          </div>

          <form onSubmit={handle} className="flex flex-col gap-4">
            {/* Name — register only */}
            {tab === 'register' && (
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Имя</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="Как вас зовут?"
                  maxLength={50}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
              </div>
            )}

            {/* Email */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Пароль</label>
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder={tab === 'register' ? 'Минимум 6 символов' : '••••••••'}
                minLength={tab === 'register' ? 6 : undefined}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              />
            </div>

            {/* Error */}
            {error && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl font-semibold text-sm bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed text-white transition-colors mt-1"
            >
              {loading
                ? (tab === 'login' ? 'Входим...' : 'Регистрируемся...')
                : (tab === 'login' ? 'Войти' : 'Создать аккаунт')}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
