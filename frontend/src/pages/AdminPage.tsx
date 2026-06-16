import { useState, useEffect } from 'react'
import Header from '../components/Header'
import StaffAnswerList from '../components/StaffAnswerList'
import LoginForm from '../components/LoginForm'
import SessionList from '../components/SessionList'
import { api } from '../api/client'
import type { StaffSession, StaffSessionDetail } from '../api/client'

export default function AdminPage() {
  const [authed, setAuthed] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState(false)
  const [sessions, setSessions] = useState<StaffSession[]>([])
  const [detail, setDetail] = useState<StaffSessionDetail | null>(null)
  const [profileFilter, setProfileFilter] = useState('')
  const [codeFilter, setCodeFilter] = useState('')
  const [exporting, setExporting] = useState(false)

  // Detect an existing auth cookie on mount; no credentials are stored client-side.
  useEffect(() => {
    api.authMe().then(() => setAuthed(true)).catch(() => setAuthed(false))
  }, [])

  useEffect(() => {
    if (!authed) return
    fetchSessions()
  }, [authed, profileFilter, codeFilter])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.login(username, password)
      setPassword('')
      setAuthed(true)
      setAuthError(false)
    } catch {
      setAuthError(true)
    }
  }

  async function fetchSessions() {
    const params: Record<string, string> = {}
    if (profileFilter) params.profile = profileFilter
    if (codeFilter) params.code = codeFilter
    try {
      const data = await api.getAdminSessions(params)
      setSessions(data)
    } catch (err: any) {
      if (err.status === 401) setAuthed(false)
    }
  }

  async function handleRowClick(code: string) {
    const d = await api.getAdminSessionDetail(code)
    setDetail(d)
  }

  async function handleExport() {
    setExporting(true)
    try {
      const resp = await api.exportAdmin()
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'sessions.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setExporting(false)
    }
  }

  if (!authed) {
    return (
      <LoginForm
        title="Admin"
        username={username}
        password={password}
        onUsername={setUsername}
        onPassword={setPassword}
        onSubmit={handleLogin}
        error={authError}
      />
    )
  }

  if (detail) {
    return (
      <div className="min-h-screen bg-cream text-ink font-sans">
        <Header />
        <div className="max-w-lg mx-auto px-6 py-8">
          <button onClick={() => setDetail(null)} className="text-brand-dark underline text-sm mb-4">
            ← Terug
          </button>
          <h2 className="font-display text-xl font-bold mb-1">Sessie {detail.session_code}</h2>
          <p className="text-sm text-ink/70 mb-4">{detail.source} · Profiel {detail.profile} · {detail.started_at.slice(0, 10)} · {detail.status}</p>
          {detail.email_failed_warning && (
            <p className="bg-danger/10 text-danger text-sm p-3 rounded-card mb-4">
              E-mail naar medewerker niet verzonden. Gebruik de sessiecode.
            </p>
          )}
          <section className="mb-4">
            <h3 className="font-semibold text-ink mb-2">Antwoorden</h3>
            <StaffAnswerList answers={detail.quiz_answers} />
          </section>
          {detail.optional_note && (
            <section className="mb-4">
              <h3 className="font-semibold text-ink mb-1">Extra info</h3>
              <p className="text-sm text-ink/80">{detail.optional_note}</p>
            </section>
          )}
          <section className="mb-4">
            <h3 className="font-semibold text-ink mb-2">Bekeken producten</h3>
            <p className="text-sm text-ink/70">{detail.shown_products.flat().join(', ') || '—'}</p>
          </section>
          <section className="mb-4">
            <h3 className="font-semibold text-ink mb-1">Favorieten</h3>
            <p className="text-sm text-ink/70">Kinderwagens: {detail.stroller_favorites.join(', ') || '—'}</p>
            <p className="text-sm text-ink/70">Accessoires: {detail.accessory_favorites.join(', ') || '—'}</p>
          </section>
          {detail.talking_points && detail.talking_points.length > 0 && (
            <section className="mb-4">
              <h3 className="font-semibold text-ink mb-2">Gespreksopeners</h3>
              <ul className="space-y-1">
                {detail.talking_points.map((tp, i) => (
                  <li key={i} className="text-sm text-ink/80">• {tp}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-cream text-ink font-sans">
      <Header />
      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="font-display text-2xl font-bold">Admin — Sessies</h1>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="bg-brand text-ink rounded-btn px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {exporting ? 'Exporteren…' : 'Download XLSX'}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-3 mb-6">
          <select
            value={profileFilter}
            onChange={(e) => setProfileFilter(e.target.value)}
            className="border-2 border-muted rounded-card px-3 py-2 bg-white text-sm outline-none focus:border-brand"
          >
            <option value="">Alle profielen</option>
            <option value="A">A — Minimalist</option>
            <option value="B">B — Ontdekker</option>
            <option value="C">C — Planner</option>
          </select>
          <input
            placeholder="Sessiecode" value={codeFilter}
            onChange={(e) => setCodeFilter(e.target.value)}
            className="border-2 border-muted rounded-card px-3 py-2 bg-white text-sm outline-none focus:border-brand"
          />
        </div>
        <SessionList sessions={sessions} onSelect={handleRowClick} emptyLabel="Geen sessies." />
      </div>
    </div>
  )
}
