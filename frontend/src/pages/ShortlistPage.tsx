import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'
import { useState } from 'react'

export default function ShortlistPage() {
  const navigate = useNavigate()
  const {
    source, strollerFavorites, accessoryFavorites, recommendations, setHandoff, setEmailStatus, setStatus,
    setFavorites,
  } = useSessionStore()
  const [busyId, setBusyId] = useState<string | null>(null)

  const allStrollers = recommendations.flat()
  const favStrollers = allStrollers.filter((s) => strollerFavorites.includes(s.id))
  const accessoryMap = new Map(
    allStrollers.flatMap((stroller) => stroller.cross_sell_items.map((accessory) => [accessory.id, accessory]))
  )
  const favAccessories = accessoryFavorites
    .map((id) => accessoryMap.get(id))
    .filter((accessory): accessory is NonNullable<typeof accessory> => Boolean(accessory))

  async function handleConfirm() {
    const result = await api.handoff()
    setHandoff(result.session_code, result.handoff_at)
    setEmailStatus(result.email_status as 'pending')
    setStatus('handoff')
    if (source === 'store') navigate('/handoff')
    else navigate('/complete')
  }

  async function handleRemoveFavorite(id: string, type: 'stroller' | 'accessory') {
    setBusyId(id)
    try {
      const result = await api.toggleFavorite(id, type)
      setFavorites(result.stroller_favorites, result.accessory_favorites)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="min-h-screen bg-cream text-ink font-sans pb-24">
      <Header />
      <div className="max-w-4xl mx-auto px-6 py-8">
        <h1 className="font-display text-2xl font-bold text-ink mb-1">Jullie favorieten</h1>
        <p className="text-ink/60 mb-6">Deze items hebben jullie bewaard.</p>

        {strollerFavorites.length === 0 && accessoryFavorites.length === 0 ? (
          <p className="text-ink/50 italic">Jullie hebben nog geen favorieten bewaard.</p>
        ) : (
          <>
            {favStrollers.length > 0 && (
              <div className="mb-6">
                <h2 className="font-semibold text-ink mb-2">Kinderwagens</h2>
                <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {favStrollers.map((s) => (
                    <li key={s.id} className="bg-white rounded-card p-3 border border-muted">
                      {s.image_url && (
                        <img src={s.image_url} alt={s.name} className="w-full h-32 object-contain mb-2" />
                      )}
                      <p className="text-xs font-semibold tracking-widest uppercase text-ink/60 mb-0.5">{s.brand}</p>
                      <p className="font-medium text-ink leading-snug mb-1 min-h-12">{s.name}</p>
                      <div className="flex items-center justify-between">
                        <p className="text-ink/70 text-sm">€ {s.price.toFixed(2)}</p>
                        <button
                          onClick={() => handleRemoveFavorite(s.id, 'stroller')}
                          disabled={busyId === s.id}
                          className="text-sm border border-muted rounded-btn px-2 py-1 disabled:opacity-50"
                        >
                          Verwijder
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {accessoryFavorites.length > 0 && (
              <div className="mb-6">
                <h2 className="font-semibold text-ink mb-2">Accessoires</h2>
                {favAccessories.length > 0 ? (
                  <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {favAccessories.map((a) => (
                      <li key={a.id} className="bg-white rounded-card p-3 border border-muted">
                        {a.image_url && (
                          <img src={a.image_url} alt={a.name} className="w-full h-32 object-contain mb-2" />
                        )}
                        <p className="text-xs font-semibold tracking-widest uppercase text-ink/60 mb-0.5">{a.brand}</p>
                        <p className="font-medium text-ink leading-snug mb-1 min-h-12">{a.name}</p>
                        <div className="flex items-center justify-between">
                          <p className="text-ink/70 text-sm">€ {a.price.toFixed(2)}</p>
                          <button
                            onClick={() => handleRemoveFavorite(a.id, 'accessory')}
                            disabled={busyId === a.id}
                            className="text-sm border border-muted rounded-btn px-2 py-1 disabled:opacity-50"
                          >
                            Verwijder
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <ul className="space-y-1">
                    {accessoryFavorites.map((id) => (
                      <li key={id} className="text-ink/70 text-sm flex items-center justify-between gap-2">
                        <span>{id}</span>
                        <button
                          onClick={() => handleRemoveFavorite(id, 'accessory')}
                          disabled={busyId === id}
                          className="text-sm border border-muted rounded-btn px-2 py-1 disabled:opacity-50"
                        >
                          Verwijder
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </>
        )}
      </div>

      <div className="fixed bottom-0 left-0 right-0 bg-cream border-t border-muted p-4 flex flex-col gap-3 max-w-lg mx-auto">
        <button
          onClick={handleConfirm}
          className="w-full bg-brand text-white rounded-btn px-6 py-3 font-medium"
        >
          Deel met medewerker
        </button>
        <button
          onClick={() => navigate('/recommendations')}
          className="w-full border border-brand text-brand rounded-btn px-6 py-3 font-medium"
        >
          Terug naar aanbevelingen
        </button>
      </div>
    </div>
  )
}
