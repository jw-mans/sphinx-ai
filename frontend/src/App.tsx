import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import { AuthPage } from './pages/AuthPage'
import { HomePage } from './pages/HomePage'
import { InterviewPage } from './pages/InterviewPage'
import { ResultPage } from './pages/ResultPage'

export default function App() {
  const { token, user, loading, saveSession, logout } = useAuth()

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

  if (!token || !user) {
    return <AuthPage onSuccess={({ access_token, user }) => saveSession(access_token, user)} />
  }

  return (
    <Routes>
      <Route path="/" element={<HomePage user={user} onLogout={logout} />} />
      <Route path="/interview/:interviewId" element={<InterviewPage />} />
      <Route path="/result/:interviewId" element={<ResultPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
