import { useEffect } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import type { Question } from '../api/interview'
import { useInterview, TOTAL_QUESTIONS } from '../hooks/useInterview'
import { QuestionCard } from '../components/QuestionCard'
import { AnswerEditor } from '../components/AnswerEditor'
import { FeedbackView } from '../components/FeedbackView'

export function InterviewPage() {
  const { interviewId: rawId } = useParams<{ interviewId: string }>()
  const location = useLocation()
  const navigate = useNavigate()

  const interviewId = Number(rawId)
  const firstQuestion = (location.state as { firstQuestion?: Question } | null)?.firstQuestion

  const { phase, question, evaluation, questionNumber, error, isSubmitting, submitAnswer, nextQuestion, retry } =
    useInterview(interviewId, firstQuestion)

  useEffect(() => {
    if (phase === 'completed') {
      navigate(`/result/${interviewId}`, { replace: true })
    }
  }, [phase, interviewId, navigate])

  const isLastQuestion = questionNumber >= TOTAL_QUESTIONS
  const progress = Math.round((questionNumber / TOTAL_QUESTIONS) * 100)

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-lg">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-slate-500 text-sm">sphinx</span>
          <span className="text-slate-500 text-sm">
            {questionNumber} / {TOTAL_QUESTIONS}
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-1 rounded-full bg-slate-800 mb-6">
          <div
            className="h-1 rounded-full bg-indigo-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Loading spinner */}
        {phase === 'loading' && (
          <div className="flex items-center justify-center py-20">
            <svg className="animate-spin h-8 w-8 text-indigo-500" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          </div>
        )}

        {/* Error state */}
        {phase === 'error' && (
          <div className="flex flex-col gap-4">
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
              {error}
            </div>
            <button
              onClick={retry}
              className="w-full py-3 rounded-xl font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
            >
              Попробовать снова
            </button>
          </div>
        )}

        {/* Answering phase */}
        {phase === 'answering' && question && (
          <div className="flex flex-col gap-5">
            <QuestionCard question={question} number={questionNumber} />
            {error && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
                {error}
              </div>
            )}
            <AnswerEditor onSubmit={submitAnswer} isSubmitting={isSubmitting} />
          </div>
        )}

        {/* Feedback phase */}
        {phase === 'feedback' && evaluation && (
          <div className="flex flex-col gap-5">
            {question && <QuestionCard question={question} number={questionNumber} />}
            <FeedbackView
              evaluation={evaluation}
              onNext={nextQuestion}
              loading={false}
              isLast={isLastQuestion}
            />
          </div>
        )}
      </div>
    </div>
  )
}
