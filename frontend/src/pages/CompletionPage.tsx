import { useEffect } from 'react'
import Header from '../components/Header'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'

const EMAIL_COPY: Record<string, string> = {
  pending: 'Bezig met delen…',
  sent: 'Gedeeld met medewerker',
  failed: 'Vraag de medewerker om je sessiecode te gebruiken.',
}

export default function CompletionPage() {
  const { sessionCode, handoffAt, emailStatus, setEmailStatus } = useSessionStore()

  useEffect(() => {
    if (emailStatus !== 'pending') return
    const interval = setInterval(async () => {
      try {
        const session = await api.getSession()
        if (session.email_status !== 'pending') {
          setEmailStatus(session.email_status as 'sent' | 'failed')
          clearInterval(interval)
        }
      } catch {}
    }, 5000)
    return () => clearInterval(interval)
  }, [emailStatus, setEmailStatus])

  return (
    <div className="min-h-screen bg-cream text-ink font-sans">
      <Header />
      <div className="max-w-lg mx-auto px-6 py-12 flex flex-col items-center text-center gap-6">
        <p className="text-ink/60 text-sm font-medium uppercase tracking-widest">Jullie sessiecode</p>
        <div className="font-mono text-4xl font-bold bg-brand/10 text-ink px-8 py-4 rounded-card tracking-widest">
          {sessionCode}
        </div>
        <p className="text-ink/70">Klaar! De medewerker kan jullie profiel ophalen met deze code.</p>
        {handoffAt && (
          <p className="text-ink/50 text-sm">
            Aangemaakt op {new Date(handoffAt).toLocaleString('nl-BE')}
          </p>
        )}
        <p className={`text-sm font-medium ${emailStatus === 'failed' ? 'text-danger' : 'text-ink/60'}`}>
          {EMAIL_COPY[emailStatus] || ''}
        </p>
      </div>
    </div>
  )
}
