import { useEffect, useState } from 'react'
import Header from '../components/Header'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'
import type { StaffSessionDetail } from '../api/client'

const PROFILE_LABELS: Record<string, string> = {
  A: 'Minimalist',
  B: 'Ontdekker',
  C: 'Planner',
}

export default function StaffHandoffPage() {
  const { sessionCode, reset } = useSessionStore()
  const [detail, setDetail] = useState<StaffSessionDetail | null>(null)

  useEffect(() => {
    const creds = sessionStorage.getItem('staff_creds')
    if (sessionCode && creds) {
      api.getStaffSessionDetail(sessionCode, creds).then(setDetail).catch(() => {})
    }
  }, [sessionCode])

  function handleNewClient() {
    reset()
    sessionStorage.removeItem('staff_creds')
    window.location.href = '/?source=store'
  }

  return (
    <div className="min-h-screen bg-cream text-ink font-sans pb-24">
      <Header />
      <div className="max-w-lg mx-auto px-6 py-8">
        {detail ? (
          <>
            <section className="mb-6">
              <h2 className="font-semibold text-ink mb-1">Gedragsprofiel</h2>
              <p className="text-brand font-display text-xl">{PROFILE_LABELS[detail.profile || ''] || detail.profile}</p>
            </section>

            <section className="mb-6">
              <h2 className="font-semibold text-ink mb-2">Antwoorden</h2>
              <ul className="space-y-1">
                {detail.quiz_answers.map((a: any, i: number) => (
                  <li key={i} className="text-sm text-ink/80">
                    <span className="font-medium">{a.question_text}: </span>{a.option_text}
                  </li>
                ))}
              </ul>
            </section>

            {detail.optional_note && (
              <section className="mb-6">
                <h2 className="font-semibold text-ink mb-1">Extra info</h2>
                <p className="text-ink/80 text-sm">{detail.optional_note}</p>
              </section>
            )}

            <section className="mb-6">
              <h2 className="font-semibold text-ink mb-2">Bekeken producten</h2>
              <p className="text-ink/60 text-sm">{detail.shown_products.flat().join(', ') || '—'}</p>
            </section>

            <section className="mb-6">
              <h2 className="font-semibold text-ink mb-2">Favorieten</h2>
              {detail.stroller_favorites.length > 0 && (
                <>
                  <h3 className="text-sm font-medium text-ink/70 mb-1">Kinderwagens</h3>
                  <p className="text-sm text-ink/60">{detail.stroller_favorites.join(', ')}</p>
                </>
              )}
              {detail.accessory_favorites.length > 0 && (
                <>
                  <h3 className="text-sm font-medium text-ink/70 mt-2 mb-1">Accessoires</h3>
                  <p className="text-sm text-ink/60">{detail.accessory_favorites.join(', ')}</p>
                </>
              )}
            </section>

            {detail.talking_points && detail.talking_points.length > 0 && (
              <section className="mb-6">
                <h2 className="font-semibold text-ink mb-2">Gespreksopeners</h2>
                <ul className="space-y-1">
                  {detail.talking_points.map((tp, i) => (
                    <li key={i} className="text-sm text-ink/80">• {tp}</li>
                  ))}
                </ul>
              </section>
            )}
          </>
        ) : (
          <p className="text-ink/50">Sessiedetails laden…</p>
        )}
      </div>

      <div className="fixed bottom-0 left-0 right-0 bg-cream border-t border-muted p-4">
        <button
          onClick={handleNewClient}
          className="w-full max-w-lg mx-auto block bg-danger text-white rounded-btn px-6 py-3 font-medium"
        >
          Nieuwe klant
        </button>
      </div>
    </div>
  )
}
