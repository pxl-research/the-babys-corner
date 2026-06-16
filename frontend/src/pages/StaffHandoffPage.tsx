import { useEffect, useState } from 'react'
import Header from '../components/Header'
import StaffAnswerList from '../components/StaffAnswerList'
import FavoriteCard from '../components/FavoriteCard'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'
import type { SessionState } from '../api/client'

const PROFILE_LABELS: Record<string, string> = {
  A: 'Minimalist',
  B: 'Ontdekker',
  C: 'Planner',
}

function namedLine(items: { name: string; brand: string }[]): string {
  return items.map((i) => `${i.name} — ${i.brand}`).join(', ') || '—'
}

export default function StaffHandoffPage() {
  const { reset } = useSessionStore()
  const [detail, setDetail] = useState<SessionState | null>(null)
  const [pointsExhausted, setPointsExhausted] = useState(false)

  useEffect(() => {
    let attempts = 0
    let cancelled = false

    async function load() {
      try {
        const session = await api.getSession()
        if (!cancelled) setDetail(session)
        if (session.talking_points?.length) return
        if (attempts >= 3) {
          if (!cancelled) setPointsExhausted(true)
          return
        }
        attempts += 1
        window.setTimeout(load, 5000)
      } catch {
        if (!cancelled) setDetail(null)
      }
    }

    load()
    return () => { cancelled = true }
  }, [])

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
            <section className="mb-8">
              <h2 className="font-display text-2xl font-bold text-ink mb-1">Favorieten van de klant</h2>
              <p className="text-ink/70 text-sm mb-4">De producten die de klant zelf bewaarde.</p>

              {detail.stroller_favorites_named.length === 0 &&
                detail.accessory_favorites_named.length === 0 && (
                  <p className="text-sm text-ink/70">Nog geen favorieten bewaard.</p>
                )}

              {detail.stroller_favorites_named.length > 0 && (
                <>
                  <h3 className="text-sm font-semibold text-ink/70 mb-2">Kinderwagens</h3>
                  <div className="grid grid-cols-2 gap-3 mb-5">
                    {detail.stroller_favorites_named.map((item) => (
                      <FavoriteCard key={item.id} item={item} />
                    ))}
                  </div>
                </>
              )}

              {detail.accessory_favorites_named.length > 0 && (
                <>
                  <h3 className="text-sm font-semibold text-ink/70 mb-2">Accessoires</h3>
                  <div className="grid grid-cols-2 gap-3">
                    {detail.accessory_favorites_named.map((item) => (
                      <FavoriteCard key={item.id} item={item} />
                    ))}
                  </div>
                </>
              )}
            </section>

            {(detail.contact_name || detail.contact_surname || detail.contact_email) && (
              <section className="mb-6 bg-white rounded-card border border-muted p-4">
                <h2 className="font-semibold text-ink mb-1">Contactgegevens klant</h2>
                {(detail.contact_name || detail.contact_surname) && (
                  <p className="text-sm text-ink/80">
                    {[detail.contact_name, detail.contact_surname].filter(Boolean).join(' ')}
                  </p>
                )}
                {detail.contact_email && (
                  <a href={`mailto:${detail.contact_email}`} className="text-sm text-brand-dark underline">
                    {detail.contact_email}
                  </a>
                )}
              </section>
            )}

            <section className="mb-6">
              <h2 className="font-semibold text-ink mb-1">Gedragsprofiel</h2>
              <p className="text-brand-dark font-display text-xl">{PROFILE_LABELS[detail.profile || ''] || detail.profile}</p>
            </section>

            <section className="mb-6">
              <h2 className="font-semibold text-ink mb-2">Antwoorden</h2>
              <StaffAnswerList answers={detail.quiz_answers} />
            </section>

            {detail.optional_note && (
              <section className="mb-6">
                <h2 className="font-semibold text-ink mb-1">Extra info</h2>
                <p className="text-ink/80 text-sm">{detail.optional_note}</p>
              </section>
            )}

            <section className="mb-6">
              <h2 className="font-semibold text-ink mb-2">Bekeken producten</h2>
              <p className="text-ink/70 text-sm">{namedLine(detail.shown_products_named.flat())}</p>
            </section>

            <section className="mb-6">
              <h2 className="font-semibold text-ink mb-2">Gespreksopeners</h2>
              {detail.talking_points && detail.talking_points.length > 0 ? (
                <ul className="space-y-1">
                  {detail.talking_points.map((tp, i) => (
                    <li key={i} className="text-sm text-ink/80">• {tp}</li>
                  ))}
                </ul>
              ) : pointsExhausted ? (
                <p className="text-sm text-ink/70">Gespreksopeners nog niet beschikbaar.</p>
              ) : (
                <p className="text-sm text-ink/70">Gespreksopeners worden gegenereerd…</p>
              )}
            </section>
          </>
        ) : (
          <p className="text-ink/70">Sessiedetails laden…</p>
        )}
      </div>

      <div className="fixed bottom-0 left-0 right-0 bg-cream border-t border-muted p-4">
        <button
          onClick={handleNewClient}
          className="w-full max-w-lg mx-auto block bg-brand text-ink rounded-btn px-6 py-3 font-medium"
        >
          Nieuwe klant
        </button>
      </div>
    </div>
  )
}
