import { BrowserRouter, Routes, Route } from 'react-router-dom'
import WelcomePage from './pages/WelcomePage'
import QuizPage from './pages/QuizPage'
import TransitionPage from './pages/TransitionPage'
import RecommendationsPage from './pages/RecommendationsPage'
import ShortlistPage from './pages/ShortlistPage'
import CompletionPage from './pages/CompletionPage'
import StaffHandoffPage from './pages/StaffHandoffPage'
import StaffLookupPage from './pages/StaffLookupPage'
import AdminPage from './pages/AdminPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<WelcomePage />} />
        <Route path="/quiz/:step" element={<QuizPage />} />
        <Route path="/transition" element={<TransitionPage />} />
        <Route path="/recommendations" element={<RecommendationsPage />} />
        <Route path="/shortlist" element={<ShortlistPage />} />
        <Route path="/complete" element={<CompletionPage />} />
        <Route path="/handoff" element={<StaffHandoffPage />} />
        <Route path="/staff" element={<StaffLookupPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </BrowserRouter>
  )
}
