import { useEffect, useState } from 'react'
import type { Evaluation } from '../api/interview'

const SCORE_FIELDS: { key: keyof Evaluation['score']; label: string }[] = [
  { key: 'correctness', label: 'Правильность' },
  { key: 'optimality', label: 'Оптимальность' },
  { key: 'complexity', label: 'Понимание сложности' },
  { key: 'explanation', label: 'Объяснение' },
  { key: 'gaps', label: 'Пробелы в знаниях' },
]

function scoreColor(value: number): string {
  if (value >= 8) return 'bg-emerald-500'
  if (value >= 6) return 'bg-blue-500'
  if (value >= 4) return 'bg-amber-500'
  return 'bg-rose-500'
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const id = requestAnimationFrame(() => setWidth(Math.round((value / 10) * 100)))
    return () => cancelAnimationFrame(id)
  }, [value])

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-slate-400">{label}</span>
        <span className="text-sm font-semibold text-slate-200">{value}/10</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800">
        <div
          className={`h-2 rounded-full transition-[width] duration-700 ease-out ${scoreColor(value)}`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  )
}

interface Props {
  evaluation: Evaluation
  onNext: () => void
  loading: boolean
  isLast?: boolean
}

export function FeedbackView({ evaluation, onNext, loading, isLast = false }: Props) {
  const avg = Object.values(evaluation.score).reduce((a, b) => a + b, 0) / 5

  return (
    <div className="flex flex-col gap-5">
      {/* Overall score */}
      <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 rounded-xl p-4">
        <div className="text-4xl font-bold text-indigo-400 tabular-nums min-w-[3.5rem] text-center">
          {avg.toFixed(1)}
        </div>
        <div>
          <div className="text-sm font-medium text-slate-200">Средняя оценка</div>
          <div className="text-xs text-slate-500">из 10 по 5 критериям</div>
        </div>
      </div>

      {/* Score bars */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-4">
        {SCORE_FIELDS.map(f => (
          <ScoreBar key={f.key} label={f.label} value={evaluation.score[f.key]} />
        ))}
      </div>

      {/* Feedback text */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-slate-300 mb-2">Обратная связь</h3>
        <p className="text-sm text-slate-400 leading-relaxed">{evaluation.feedback}</p>
      </div>

      {/* Weak topics */}
      {evaluation.weak_topics && evaluation.weak_topics.length > 0 && (
        <div className="bg-slate-900 border border-rose-500/20 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-rose-400 mb-2">Стоит подтянуть</h3>
          <div className="flex flex-wrap gap-2">
            {evaluation.weak_topics.map(topic => (
              <span
                key={topic}
                className="text-xs px-2 py-1 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-300"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Next question button */}
      <button
        onClick={onNext}
        disabled={loading}
        className="w-full py-3 rounded-xl font-semibold transition-all bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-white"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Загружаем...
          </span>
        ) : isLast ? (
          'Завершить интервью →'
        ) : (
          'Следующий вопрос →'
        )}
      </button>
    </div>
  )
}
