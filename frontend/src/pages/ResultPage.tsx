import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getInterviewResult } from '../api/interview'
import type { InterviewResult, Score, SessionSummary } from '../api/interview'

const SCORE_FIELDS: { key: keyof Score; label: string; color: string }[] = [
  { key: 'correctness', label: 'Правильность', color: 'bg-emerald-500' },
  { key: 'optimality', label: 'Оптимальность', color: 'bg-blue-500' },
  { key: 'complexity', label: 'Понимание сложности', color: 'bg-violet-500' },
  { key: 'explanation', label: 'Объяснение', color: 'bg-amber-500' },
  { key: 'gaps', label: 'Пробелы в знаниях', color: 'bg-rose-500' },
]

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-slate-400">{label}</span>
        <span className="text-sm font-semibold text-slate-200">{value.toFixed(1)}/10</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${(value / 10) * 100}%` }} />
      </div>
    </div>
  )
}

function SummarySection({ summary }: { summary: SessionSummary }) {
  return (
    <div className="bg-slate-900 border border-indigo-500/20 rounded-xl p-5 flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-indigo-300">Итоговое саммари</h2>

      <p className="text-sm text-slate-300 leading-relaxed">{summary.overall}</p>

      {summary.strengths.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-emerald-400 mb-2">Сильные стороны</p>
          <ul className="flex flex-col gap-1">
            {summary.strengths.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                <span className="text-emerald-500 mt-0.5">✓</span>
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {summary.weaknesses.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-rose-400 mb-2">Слабые места</p>
          <ul className="flex flex-col gap-1">
            {summary.weaknesses.map((w, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                <span className="text-rose-500 mt-0.5">✗</span>
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {summary.recommendations.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-amber-400 mb-2">Рекомендации</p>
          <ol className="flex flex-col gap-1 list-none">
            {summary.recommendations.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                <span className="text-amber-500 shrink-0">{i + 1}.</span>
                {r}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}

function getGrade(score: number): { label: string; color: string } {
  if (score >= 8.5) return { label: 'Отлично', color: 'text-emerald-400' }
  if (score >= 7) return { label: 'Хорошо', color: 'text-blue-400' }
  if (score >= 5) return { label: 'Удовлетворительно', color: 'text-amber-400' }
  return { label: 'Нужно поработать', color: 'text-rose-400' }
}

export function ResultPage() {
  const { interviewId: rawId } = useParams<{ interviewId: string }>()
  const navigate = useNavigate()
  const interviewId = Number(rawId)

  const [result, setResult] = useState<InterviewResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const onRestart = () => navigate('/')

  useEffect(() => {
    getInterviewResult(interviewId)
      .then(setResult)
      .catch(e => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [interviewId])

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

  if (error || !result) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-4">
        <p className="text-rose-400 text-sm">{error ?? 'Результаты недоступны'}</p>
        <button onClick={onRestart} className="px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors">
          На главную
        </button>
      </div>
    )
  }

  const overallAvg =
    Object.values(result.average_score).reduce((a, b) => a + b, 0) / 5
  const grade = getGrade(overallAvg)

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-10">
      <div className="w-full max-w-lg flex flex-col gap-6">
        {/* Header */}
        <div className="text-center">
          <div className="text-5xl font-bold text-indigo-400 tabular-nums mb-1">
            {overallAvg.toFixed(1)}
          </div>
          <div className={`text-lg font-semibold ${grade.color}`}>{grade.label}</div>
          <div className="text-slate-500 text-sm mt-1">
            {result.questions_results.length} вопросов пройдено
          </div>
        </div>

        {/* Average scores */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
          <h2 className="text-sm font-semibold text-slate-300">Средние баллы</h2>
          {SCORE_FIELDS.map(f => (
            <ScoreBar key={f.key} label={f.label} value={result.average_score[f.key]} color={f.color} />
          ))}
        </div>

        {/* Session summary */}
        {result.summary && <SummarySection summary={result.summary} />}

        {/* Per-question breakdown */}
        <div className="flex flex-col gap-4">
          <h2 className="text-sm font-semibold text-slate-300">Разбор по вопросам</h2>
          {result.questions_results.map((qr, i) => {
            const qAvg = Object.values(qr.score).reduce((a, b) => a + b, 0) / 5
            return (
              <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <p className="text-sm text-slate-300 leading-snug flex-1">{qr.question}</p>
                  <span className="text-sm font-bold text-indigo-400 tabular-nums shrink-0">
                    {qAvg.toFixed(1)}
                  </span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">{qr.feedback}</p>
                {qr.weak_topics?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {qr.weak_topics.map(t => (
                      <span key={t} className="text-xs px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Restart */}
        <button
          onClick={onRestart}
          className="w-full py-3 rounded-xl font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
        >
          Пройти ещё раз
        </button>
      </div>
    </div>
  )
}
