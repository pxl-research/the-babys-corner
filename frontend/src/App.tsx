import { BrowserRouter, Routes, Route } from 'react-router-dom'

function Placeholder({ name }: { name: string }) {
  return (
    <div className="min-h-screen bg-cream text-ink flex items-center justify-center">
      <p className="font-display text-2xl">{name}</p>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Placeholder name="WelcomePage" />} />
        <Route path="/quiz/:step" element={<Placeholder name="QuizPage" />} />
        <Route path="/transition" element={<Placeholder name="TransitionPage" />} />
        <Route path="/recommendations" element={<Placeholder name="RecommendationsPage" />} />
        <Route path="/shortlist" element={<Placeholder name="ShortlistPage" />} />
        <Route path="/complete" element={<Placeholder name="CompletionPage" />} />
        <Route path="/handoff" element={<Placeholder name="StaffHandoffPage" />} />
        <Route path="/staff" element={<Placeholder name="StaffLookupPage" />} />
        <Route path="/admin" element={<Placeholder name="AdminPage" />} />
      </Routes>
    </BrowserRouter>
  )
}
