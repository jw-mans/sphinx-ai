import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { getInterviewHistory, getCompetencyProfile } from '../api/interview'
import type { InterviewHistoryItem, CompetencyProfile } from '../api/interview'
import type { UserOut } from '../api/auth'
import { CompetencyMap } from '../components/CompetencyMap'

interface Props {
  user: UserOut
}

function levelBadge(level: string) {
  const map: Record<string, string> = {
    junior: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
    middle: 'text-amber-400  bg-amber-500/10  border-amber-500/30',
    senior: 'text-rose-400   bg-rose-500/10   border-rose-500/30',
  }
  return map[level] ?? 'text-slate-400 bg-slate-800 border-slate-700'
}

export function ProfilePage({ user }: Props) {
  const navigate = useNavigate()
  const [history, setHistory] = useState<InterviewHistoryItem[]>([])
  const [competency, setCompetency] = useState<CompetencyProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Both fetches run in parallel — no sequential GUI blocking (UJ-10)
  useEffect(() => {
    Promise.all([getInterviewHistory(), getCompetencyProfile()])
      .then(([hist, comp]) => {
        setHistory(hist)
        setCompetency(comp)
      })
      .catch(e => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [])

  const displayName = user.name ?? user.email ?? 'пользователь'

  const scoredInterviews = history.filter(h => h.average_score !== null)
  const overallAvg =
    scoredInterviews.length > 0
      ? scoredInterviews.reduce((sum, h) => sum + (h.average_score ?? 0), 0) /
        scoredInterviews.length
      : null

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <svg className="animate-spin h-8 w-8 text-indigo-500" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-10">
      <div className="w-full max-w-lg flex flex-col gap-6">

        {/* Back */}
        <button
          onClick={() => navigate('/')}
          className="self-start flex items-center gap-1 text-sm text-slate-500 hover:text-slate-300 transition-colors"
        >
          ← Главная
        </button>

        {/* User card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-lg font-bold text-indigo-400 shrink-0">
              {displayName[0].toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-slate-100 font-semibold truncate">{displayName}</p>
              {user.email && (
                <p className="text-xs text-slate-500 truncate">{user.email}</p>
              )}
              {user.telegram_id && !user.email && (
                <p className="text-xs text-slate-500">Telegram</p>
              )}
            </div>
          </div>
          {user.preferred_stack && (
            <div className="flex flex-wrap gap-1">
              {user.preferred_stack
                .split(',')
                .map(s => s.trim())
                .filter(Boolean)
                .map(s => (
                  <span
                    key={s}
                    className="text-xs px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-400"
                  >
                    {s}
                  </span>
                ))}
            </div>
          )}
        </div>

        {error && <p className="text-rose-400 text-sm text-center">{error}</p>}

        {/* Aggregate progress stats (UJ-10) */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-indigo-400 tabular-nums">
              {history.length}
            </div>
            <div className="text-xs text-slate-500 mt-1">Интервью</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-indigo-400 tabular-nums">
              {competency?.evaluated_answers ?? 0}
            </div>
            <div className="text-xs text-slate-500 mt-1">Ответов</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-indigo-400 tabular-nums">
              {overallAvg !== null ? overallAvg.toFixed(1) : '—'}
            </div>
            <div className="text-xs text-slate-500 mt-1">Средний балл</div>
          </div>
        </div>

        {/* Competency radar — aggregated across ALL past interviews */}
        {competency && competency.evaluated_answers > 0 && (
          <CompetencyMap profile={competency} />
        )}

        {/* Full interview history (UJ-8) */}
        {history.length > 0 ? (
          <div className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold text-slate-300">История интервью</h2>
            {history.map(h => (
              <Link
                key={h.interview_id}
                to={`/result/${h.interview_id}`}
                className="bg-slate-900 border border-slate-800 hover:border-slate-600 rounded-xl p-4 flex items-center justify-between transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span
                    className={`text-xs px-2 py-0.5 rounded border font-medium shrink-0 ${levelBadge(h.level)}`}
                  >
                    {h.level}
                  </span>
                  <span className="text-sm text-slate-400 truncate">{h.stack}</span>
                  <span className="text-xs text-slate-600 shrink-0">
                    {new Date(h.created_at).toLocaleDateString('ru-RU')}
                  </span>
                </div>
                <div className="flex items-center gap-3 shrink-0 ml-2">
                  <span className="text-xs text-slate-600">{h.questions_count} вопр.</span>
                  <span className="text-sm font-bold text-indigo-400 tabular-nums">
                    {h.average_score !== null ? h.average_score.toFixed(1) : '\u2014'}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          !error && (
            <div className="text-center text-slate-500 text-sm py-8">
              У вас ещё нет пройденных интервью
            </div>
          )
        )}

        {/* CTA */}
        <button
          onClick={() => navigate('/')}
          className="w-full py-3 rounded-xl font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
        >
          Пройти интервью
        </button>

      </div>
    </div>
  )
}
