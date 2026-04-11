import type { Question } from '../api/interview'

const difficultyStyle: Record<string, string> = {
  easy: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  medium: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  hard: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
}

interface Props {
  question: Question
  number: number
}

export function QuestionCard({ question, number }: Props) {
  const diffClass = difficultyStyle[question.difficulty?.toLowerCase()] ?? 'text-slate-400 bg-slate-800 border-slate-700'

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Вопрос {number}
        </span>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 rounded-md bg-slate-800 border border-slate-700 text-slate-400">
            {question.topic}
          </span>
          <span className={`text-xs px-2 py-1 rounded-md border font-medium ${diffClass}`}>
            {question.difficulty}
          </span>
        </div>
      </div>
      <p className="text-slate-100 text-base leading-relaxed">{question.text}</p>
    </div>
  )
}
