import { useState } from 'react'

const LEVELS = [
  { value: 'junior', label: 'Junior', color: 'text-emerald-400 border-emerald-500/50 bg-emerald-500/10' },
  { value: 'middle', label: 'Middle', color: 'text-amber-400 border-amber-500/50 bg-amber-500/10' },
  { value: 'senior', label: 'Senior', color: 'text-rose-400 border-rose-500/50 bg-rose-500/10' },
]

const STACKS = [
  // Языки
  'Python', 'JavaScript', 'TypeScript', 'Go', 'Java', 'C#', 'C++', 'Rust', 'Kotlin', 'Swift',
  // Frontend
  'React', 'Vue', 'Angular', 'HTML/CSS',
  // Базы данных
  'SQL', 'Redis',
  // Инфраструктура
  'Docker', 'Kubernetes', 'Linux', 'Bash',
  // API
  'GraphQL',
  // VCS
  'Git',
]

interface Props {
  onStart: (level: string, stacks: string[], notes: string) => void
  loading: boolean
}

export function InterviewStart({ onStart, loading }: Props) {
  const [level, setLevel] = useState('')
  const [stacks, setStacks] = useState<string[]>([])
  const [notes, setNotes] = useState('')

  const toggleStack = (s: string) => {
    const key = s.toLowerCase()
    setStacks(prev =>
      prev.includes(key) ? prev.filter(x => x !== key) : [...prev, key]
    )
  }

  const canStart = level && stacks.length > 0 && !loading

  return (
    <div className="flex flex-col gap-6">
      {/* Level */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">Уровень</label>
        <div className="grid grid-cols-3 gap-3">
          {LEVELS.map(l => (
            <button
              key={l.value}
              onClick={() => setLevel(l.value)}
              className={`py-3 rounded-lg border font-medium transition-all ${
                level === l.value
                  ? l.color
                  : 'text-slate-400 border-slate-700 bg-slate-900 hover:border-slate-500'
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stack — multi-select */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Технологии
          <span className="ml-2 text-slate-600 font-normal">(можно несколько)</span>
        </label>
        <div className="flex flex-wrap gap-2">
          {STACKS.map(s => {
            const key = s.toLowerCase()
            const selected = stacks.includes(key)
            return (
              <button
                key={s}
                onClick={() => toggleStack(s)}
                className={`px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                  selected
                    ? 'text-indigo-300 border-indigo-500/70 bg-indigo-500/10'
                    : 'text-slate-400 border-slate-700 bg-slate-900 hover:border-slate-500'
                }`}
              >
                {s}
              </button>
            )
          })}
        </div>
      </div>

      {/* User notes */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">
          Пожелания к темам
          <span className="ml-2 text-slate-600 font-normal">(необязательно)</span>
        </label>
        <textarea
          rows={3}
          value={notes}
          onChange={e => setNotes(e.target.value)}
          placeholder="Например: хочу больше вопросов по многопоточности и работе с базами данных..."
          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors resize-none text-sm leading-relaxed"
        />
      </div>

      {/* Start button */}
      <button
        onClick={() => onStart(level, stacks, notes.trim())}
        disabled={!canStart}
        className="w-full py-4 rounded-xl font-semibold text-base transition-all bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-white mt-2"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Начинаем...
          </span>
        ) : (
          'Начать интервью'
        )}
      </button>
    </div>
  )
}
