import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { InterviewStart } from '../components/InterviewStart'
import { startInterview } from '../api/interview'
import type { UserOut } from '../api/auth'

interface Props {
  user: UserOut
  onLogout: () => void
}

export function HomePage({ user, onLogout }: Props) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const displayName = user.name ?? user.email ?? 'пользователь'

  const handleStart = async (level: string, stacks: string[], notes: string) => {
    setLoading(true)
    setError(null)
    try {
      const stack = stacks.join(', ')
      const interview = await startInterview(user.id, level, stack, notes || undefined)
      navigate(`/interview/${interview.interview_id}`, {
        state: { firstQuestion: interview.current_question },
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Что-то пошло не так')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo / header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 mb-4">
            <svg className="w-8 h-8 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.3 24.3 0 014.5 0m0 0v5.714a2.25 2.25 0 001.357 2.059l.524.22a1.5 1.5 0 001.03 0l.524-.22a2.25 2.25 0 001.357-2.059V3.104m-6.25 0c.25.023.501.05.75.082M12 21v-3.75m0 0a2.25 2.25 0 00-2.25-2.25H7.5M12 17.25a2.25 2.25 0 012.25-2.25H16.5" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-slate-100">Sphinx</h1>
          <p className="text-slate-400 mt-2 text-sm">
            Привет, {displayName}! Готов к собеседованию?
          </p>
        </div>

        {/* Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
          <InterviewStart onStart={handleStart} loading={loading} />
        </div>

        {/* Error */}
        {error && (
          <div className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm text-center">
            {error}
          </div>
        )}

        {/* Profile & Logout */}
        <div className="mt-6 flex items-center justify-between">
          <Link
            to="/profile"
            className="text-xs text-slate-500 hover:text-indigo-400 transition-colors"
          >
            Мой профиль и история
          </Link>
          <button
            onClick={onLogout}
            className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
          >
            Выйти
          </button>
        </div>
      </div>
    </div>
  )
}
