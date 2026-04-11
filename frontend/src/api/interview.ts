const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Types

export interface User {
  id: number
  telegram_id: string
  created_at: string
}

export interface Question {
  id: number
  text: string
  topic: string
  difficulty: string
}

export interface Score {
  correctness: number
  optimality: number
  complexity: number
  explanation: number
  gaps: number
}

export interface Evaluation {
  score: Score
  feedback: string
  weak_topics: string[]
}

export interface StartInterviewResponse {
  interview_id: number
  current_question: Question
}

export interface SubmitAnswerResponse {
  evaluation: Evaluation
  next_question: Question | null
}

export interface QuestionResult {
  question: string
  answer: string
  score: Score
  feedback: string
  weak_topics: string[]
}

export interface SessionSummary {
  overall: string
  strengths: string[]
  weaknesses: string[]
  recommendations: string[]
}

export interface InterviewResult {
  average_score: Score
  questions_results: QuestionResult[]
  summary: SessionSummary | null
}

// API calls

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText)
    throw new Error(err || `HTTP ${res.status}`)
  }
  return res.json()
}

export const createUser = (telegramId: string) =>
  request<User>('/users', {
    method: 'POST',
    body: JSON.stringify({ telegram_id: telegramId }),
  })

export const startInterview = (userId: number, level: string, stack: string, userNotes?: string) =>
  request<StartInterviewResponse>('/interview/start', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, level, stack, user_notes: userNotes }),
  })

// export const getCurrentQuestion = (interviewId: number) =>
//   request<Question | { message: string }>(`/interview/${interviewId}/question`)
export const getCurrentQuestion = (interviewId: number) =>
  request<Question | { message: string }>(`/interview/${interviewId}/question/v2`)

// export const submitAnswer = (interviewId: number, text: string, code?: string) =>
//   request<SubmitAnswerResponse>(`/interview/${interviewId}/answer`, {
//     method: 'POST',
//     body: JSON.stringify({ text, code: code || undefined }),
//   })
export const submitAnswer = (interviewId: number, text: string, code?: string) =>
  request<SubmitAnswerResponse>(`/interview/${interviewId}/answer/v2`, {
    method: 'POST',
    body: JSON.stringify({ text, code: code || undefined }),
  })

// export const getInterviewResult = (interviewId: number) =>
//   request<InterviewResult>(`/interview/${interviewId}/result`)
export const getInterviewResult = (interviewId: number) =>
  request<InterviewResult>(`/interview/${interviewId}/result/v2`)
