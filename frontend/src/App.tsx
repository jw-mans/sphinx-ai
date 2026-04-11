import { Routes, Route, Navigate } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { InterviewPage } from './pages/InterviewPage'
import { ResultPage } from './pages/ResultPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/interview/:interviewId" element={<InterviewPage />} />
      <Route path="/result/:interviewId" element={<ResultPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
