import { useState } from 'react'

const MIN_ANSWER_LENGTH = 10

interface Props {
  onSubmit: (text: string, code?: string) => void
  isSubmitting: boolean
}

export function AnswerEditor({ onSubmit, isSubmitting }: Props) {
  const [text, setText] = useState('')
  const [code, setCode] = useState('')
  const [showCode, setShowCode] = useState(false)
  const [touched, setTouched] = useState(false)

  const trimmed = text.trim()
  const tooShort = trimmed.length > 0 && trimmed.length < MIN_ANSWER_LENGTH
  const canSubmit = trimmed.length >= MIN_ANSWER_LENGTH && !isSubmitting

  const handleSubmit = () => {
    if (!canSubmit) return
    onSubmit(trimmed, showCode && code.trim() ? code.trim() : undefined)
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Text answer */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="block text-sm font-medium text-slate-400">
            Ваш ответ
          </label>
          <span className={`text-xs ${tooShort ? 'text-rose-400' : 'text-slate-600'}`}>
            {trimmed.length} / {MIN_ANSWER_LENGTH} мин.
          </span>
        </div>
        <textarea
          rows={5}
          value={text}
          onChange={e => { setText(e.target.value); setTouched(true) }}
          onBlur={() => setTouched(true)}
          placeholder="Объясните своими словами..."
          className={`w-full bg-slate-900 border rounded-lg px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 transition-colors resize-none text-sm leading-relaxed ${
            touched && tooShort
              ? 'border-rose-500/60 focus:border-rose-500 focus:ring-rose-500/30'
              : 'border-slate-700 focus:border-indigo-500 focus:ring-indigo-500'
          }`}
        />
        {touched && tooShort && (
          <p className="mt-1 text-xs text-rose-400">
            Напишите хотя бы {MIN_ANSWER_LENGTH} символов
          </p>
        )}
      </div>

      {/* Code toggle */}
      <div>
        <button
          onClick={() => setShowCode(v => !v)}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
        >
          <svg
            className={`w-4 h-4 transition-transform ${showCode ? 'rotate-90' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          {showCode ? 'Скрыть код' : 'Добавить код'}
        </button>

        {showCode && (
          <textarea
            rows={8}
            value={code}
            onChange={e => setCode(e.target.value)}
            placeholder="// Ваш код здесь..."
            spellCheck={false}
            className="code-area mt-3"
          />
        )}
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="w-full py-3 rounded-xl font-semibold transition-all bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-white"
      >
        {isSubmitting ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Оцениваем...
          </span>
        ) : (
          'Отправить ответ'
        )}
      </button>
    </div>
  )
}
