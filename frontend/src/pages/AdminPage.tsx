import { useState, useEffect } from 'react'
import Header from '../components/Header'
import { api } from '../api/client'
import type { StaffSession } from '../api/client'

function encodeBasic(user: string, pass: string) {
  return btoa(`${user}:${pass}`)
}

export default function AdminPage() {
  const [creds, setCreds] = useState<string | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState(false)
  const [sessions, setSessions] = useState<StaffSession[]>([])
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
            <div key={s.session_id} className="bg-white rounded-card p-4 border border-muted text-sm">
              <div className="flex justify-between">
                <span className="font-mono font-bold">{s.session_code}</span>
                <span className="text-ink/50">{s.started_at.slice(0, 10)}</span>
              </div>
              <p className="text-ink/60 mt-0.5">{s.source} · Profiel {s.profile} · {s.status}</p>
            </div>
          ))}
          {sessions.length === 0 && <p className="text-ink/50 text-sm">Geen sessies.</p>}
        </div>
      </div>
    </div>
  )
}
