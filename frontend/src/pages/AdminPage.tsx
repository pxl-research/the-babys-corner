import { useState, useEffect } from 'react'
import Header from '../components/Header'
import StaffAnswerList from '../components/StaffAnswerList'
import { api } from '../api/client'
import type { StaffSession, StaffSessionDetail } from '../api/client'

function encodeBasic(user: string, pass: string) {
  return btoa(`${user}:${pass}`)
}

export default function AdminPage() {
  const [creds, setCreds] = useState<string | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState(false)
  const [sessions, setSessions] = useState<StaffSession[]>([])
  const [detail, setDetail] = useState<StaffSessionDetail | null>(null)
  const [profileFilter, setProfileFilter] = useState('')
  const [codeFilter, setCodeFilter] = useState('')
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    const stored = sessionStorage.getItem('admin_creds')
    if (stored) setCreds(stored)
  }, [])

  useEffect(() => {
    if (!creds) return
    fetchSessions()
  }, [creds, profileFilter, codeFilter])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    const encoded = encodeBasic(username, password)
    try {
      await api.getAdminSessions({}, encoded)
      sessionStorage.setItem('admin_creds', encoded)
      setCreds(encoded)
      setAuthError(false)
    } catch {
      setAuthError(true)
    }
  }

  async function fetchSessions() {
    if (!creds) return
    const params: Record<string, string> = {}
    if (profileFilter) params.profile = profileFilter
    if (codeFilter) params.code = codeFilter
    try {
      const data = await api.getAdminSessions(params, creds)
      setSessions(data)
    } catch (err: any) {
      if (err.status === 401) { setCreds(null); sessionStorage.removeItem('admin_creds') }
    }
  }

  async function handleRowClick(code: string) {
    if (!creds) return
    const d = await api.getAdminSessionDetail(code, creds)
    setDetail(d)
  }

  async function handleExport() {
    if (!creds) return
    setExporting(true)
    try {
      const resp = await api.exportAdmin(creds)
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

  if (!creds) {
    return (
      <div className="min-h-screen bg-cream text-ink font-sans">
        <Header />
        <div className="max-w-sm mx-auto px-6 py-12">
          <h1 className="font-display text-2xl font-bold mb-6">Admin</h1>
          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <input
              type="text" placeholder="Gebruikersnaam" value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="border-2 border-muted rounded-card px-4 py-3 bg-white outline-none focus:border-brand"
            />
            <input
              type="password" placeholder="Wachtwoord" value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="border-2 border-muted rounded-card px-4 py-3 bg-white outline-none focus:border-brand"
            />
            {authError && <p className="text-danger text-sm">Ongeldige inloggegevens.</p>}
            <button type="submit" className="bg-brand text-white rounded-btn px-6 py-3 font-medium">
              Inloggen
            </button>
          </form>
        </div>
      </div>
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
          <p className="text-sm text-ink/60 mb-4">{detail.source} · Profiel {detail.profile} · {detail.started_at.slice(0, 10)} · {detail.status}</p>
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
            <p className="text-sm text-ink/60">{detail.shown_products.flat().join(', ') || '—'}</p>
          </section>
          <section className="mb-4">
            <h3 className="font-semibold text-ink mb-1">Favorieten</h3>
            <p className="text-sm text-ink/60">Kinderwagens: {detail.stroller_favorites.join(', ') || '—'}</p>
            <p className="text-sm text-ink/60">Accessoires: {detail.accessory_favorites.join(', ') || '—'}</p>
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
            className="bg-brand text-white rounded-btn px-4 py-2 text-sm font-medium disabled:opacity-50"
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
        <div className="space-y-2">
          {sessions.map((s) => (
            <button
              key={s.session_id}
              onClick={() => handleRowClick(s.session_code)}
              className="w-full text-left bg-white rounded-card p-4 border border-muted hover:border-brand transition-colors text-sm"
            >
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-mono font-bold text-ink">{s.session_code}</p>
                  <p className="text-ink/60 mt-0.5">{s.source} · Profiel {s.profile} · {s.started_at.slice(0, 10)}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${s.status === 'handed_off' ? 'bg-brand/20 text-brand' : 'bg-muted text-ink/60'}`}>
                  {s.status}
                </span>
              </div>
            </button>
          ))}
          {sessions.length === 0 && <p className="text-ink/50 text-sm">Geen sessies.</p>}
        </div>
      </div>
    </div>
  )
}
