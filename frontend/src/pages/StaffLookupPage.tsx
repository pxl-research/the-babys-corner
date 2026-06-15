import { useState, useEffect } from 'react'
import Header from '../components/Header'
import StaffAnswerList from '../components/StaffAnswerList'
import FavoriteCard from '../components/FavoriteCard'
import LoginForm from '../components/LoginForm'
import SessionList from '../components/SessionList'
import { api } from '../api/client'
import type { StaffSession, StaffSessionDetail } from '../api/client'

export default function StaffLookupPage() {
  const [authed, setAuthed] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState(false)
  const [sessions, setSessions] = useState<StaffSession[]>([])
  const [detail, setDetail] = useState<StaffSessionDetail | null>(null)
  const [codeFilter, setCodeFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')

  // Detect an existing auth cookie on mount; no credentials are stored client-side.
  useEffect(() => {
    api.authMe().then(() => setAuthed(true)).catch(() => setAuthed(false))
  }, [])

  useEffect(() => {
    if (!authed) return
    fetchSessions()
  }, [authed, codeFilter, dateFilter, sourceFilter])

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
    if (codeFilter) params.code = codeFilter
    if (dateFilter) params.date = dateFilter
    if (sourceFilter) params.source = sourceFilter
    try {
      const data = await api.getStaffSessions(params)
      setSessions(data)
    } catch (err: any) {
      if (err.status === 401) setAuthed(false)
    }
  }

  async function handleRowClick(code: string) {
    const d = await api.getStaffSessionDetail(code)
    setDetail(d)
  }

  if (!authed) {
    return (
      <LoginForm
        title="Sessie opzoeken"
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
          <button onClick={() => setDetail(null)} className="text-brand underline text-sm mb-4">
            ← Terug
          </button>
          <h2 className="font-display text-xl font-bold mb-1">Sessie {detail.session_code}</h2>
          <p className="text-sm text-ink/60 mb-4">{detail.source} · {detail.profile} · {detail.started_at.slice(0, 10)}</p>
          {detail.email_failed_warning && (
            <p className="bg-danger/10 text-danger text-sm p-3 rounded-card mb-4">
              E-mail naar medewerker niet verzonden. Gebruik de sessiecode.
            </p>
          )}
          {(detail.contact_name || detail.contact_surname || detail.contact_email) && (
            <section className="mb-6 bg-white rounded-card border border-muted p-4">
              <h3 className="font-semibold text-ink mb-1">Contactgegevens klant</h3>
              {(detail.contact_name || detail.contact_surname) && (
                <p className="text-sm text-ink/80">
                  {[detail.contact_name, detail.contact_surname].filter(Boolean).join(' ')}
                </p>
              )}
              {detail.contact_email && (
                <a href={`mailto:${detail.contact_email}`} className="text-sm text-brand underline">
                  {detail.contact_email}
                </a>
              )}
            </section>
          )}
          <section className="mb-6">
            <h3 className="font-display text-xl font-bold text-ink mb-1">Favorieten van de klant</h3>
            <p className="text-ink/60 text-sm mb-3">De producten die de klant zelf bewaarde.</p>
            {detail.stroller_favorites_named.length === 0 &&
              detail.accessory_favorites_named.length === 0 && (
                <p className="text-sm text-ink/50">Nog geen favorieten bewaard.</p>
              )}
            {detail.stroller_favorites_named.length > 0 && (
              <>
                <h4 className="text-sm font-semibold text-ink/70 mb-2">Kinderwagens</h4>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  {detail.stroller_favorites_named.map((item) => (
                    <FavoriteCard key={item.id} item={item} />
                  ))}
                </div>
              </>
            )}
            {detail.accessory_favorites_named.length > 0 && (
              <>
                <h4 className="text-sm font-semibold text-ink/70 mb-2">Accessoires</h4>
                <div className="grid grid-cols-2 gap-3">
                  {detail.accessory_favorites_named.map((item) => (
                    <FavoriteCard key={item.id} item={item} />
                  ))}
                </div>
              </>
            )}
          </section>
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
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-cream text-ink font-sans">
      <Header />
      <div className="max-w-2xl mx-auto px-6 py-8">
        <h1 className="font-display text-2xl font-bold mb-6">Sessie opzoeken</h1>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
          <input
            placeholder="Sessiecode" value={codeFilter}
            onChange={(e) => setCodeFilter(e.target.value)}
            className="border-2 border-muted rounded-card px-3 py-2 bg-white text-sm outline-none focus:border-brand"
          />
          <input
            type="date" value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="border-2 border-muted rounded-card px-3 py-2 bg-white text-sm outline-none focus:border-brand"
          />
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="border-2 border-muted rounded-card px-3 py-2 bg-white text-sm outline-none focus:border-brand"
          >
            <option value="">Alle bronnen</option>
            <option value="home">Thuis</option>
            <option value="store">Winkel</option>
          </select>
        </div>
        <h2 className="font-semibold text-ink mb-3">Recente sessies</h2>
        <SessionList sessions={sessions} onSelect={handleRowClick} />
      </div>
    </div>
  )
}
