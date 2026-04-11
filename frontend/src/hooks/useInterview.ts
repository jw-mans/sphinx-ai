import { useState, useCallback, useEffect } from 'react'
import * as api from '../api/interview'

export const TOTAL_QUESTIONS = 5

export type InterviewPhase = 'loading' | 'answering' | 'feedback' | 'completed' | 'error'

interface InterviewState {
  phase: InterviewPhase
  question: api.Question | null
  evaluation: api.Evaluation | null
  questionNumber: number
  error: string | null
  isSubmitting: boolean
}

export function useInterview(interviewId: number, initialQuestion?: api.Question) {
  const [state, setState] = useState<InterviewState>({
    phase: initialQuestion ? 'answering' : 'loading',
    question: initialQuestion ?? null,
    evaluation: null,
    questionNumber: 1,
    error: null,
    isSubmitting: false,
  })

  const fetchNextQuestion = useCallback(async () => {
    setState(s => ({ ...s, phase: 'loading', error: null }))
    try {
      const q = await api.getCurrentQuestion(interviewId)
      if ('message' in q) {
        setState(s => ({ ...s, phase: 'completed' }))
      } else {
        setState(s => ({
          ...s,
          phase: 'answering',
          question: q,
          evaluation: null,
        }))
      }
    } catch (e) {
      setState(s => ({
        ...s,
        phase: 'error',
        error: e instanceof Error ? e.message : 'Не удалось загрузить вопрос',
      }))
    }
  }, [interviewId])

  // If no initial question, fetch on mount
  useEffect(() => {
    if (!initialQuestion) {
      fetchNextQuestion()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const submitAnswer = useCallback(
    async (text: string, code?: string) => {
      setState(s => ({ ...s, isSubmitting: true, error: null }))
      try {
        const result = await api.submitAnswer(interviewId, text, code)
        setState(s => ({
          ...s,
          isSubmitting: false,
          phase: 'feedback',
          evaluation: result.evaluation,
        }))
      } catch (e) {
        setState(s => ({
          ...s,
          isSubmitting: false,
          error: e instanceof Error ? e.message : 'Не удалось отправить ответ',
        }))
      }
    },
    [interviewId],
  )

  const nextQuestion = useCallback(async () => {
    // Complete after reaching the limit
    if (state.questionNumber >= TOTAL_QUESTIONS) {
      setState(s => ({ ...s, phase: 'completed' }))
      return
    }
    setState(s => ({ ...s, questionNumber: s.questionNumber + 1 }))
    await fetchNextQuestion()
  }, [state.questionNumber, fetchNextQuestion])

  const retry = useCallback(() => {
    fetchNextQuestion()
  }, [fetchNextQuestion])

  return { ...state, submitAnswer, nextQuestion, retry }
}
