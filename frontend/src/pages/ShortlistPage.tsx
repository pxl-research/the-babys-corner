import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import { api } from '../api/client'
import type { ShortlistItem } from '../api/client'
import { useSessionStore } from '../store/sessionStore'
import { useEffect, useRef, useState } from 'react'

export default function ShortlistPage() {
  const navigate = useNavigate()
  const {
    source, strollerFavorites, accessoryFavorites, setHandoff, setStatus,
    setFavorites,
  } = useSessionStore()
  const [busyId, setBusyId] = useState<string | null>(null)
  const [favStrollers, setFavStrollers] = useState<ShortlistItem[]>([])
  const [favAccessories, setFavAccessories] = useState<ShortlistItem[]>([])
  const [contactName, setContactName] = useState('')
  const [contactSurname, setContactSurname] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [undo, setUndo] = useState<{ id: string; type: 'stroller' | 'accessory' } | null>(null)
  const undoTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hasFavorites = strollerFavorites.length + accessoryFavorites.length > 0
  // Email is optional, but if filled it must look like an address before we hand off.
  const emailInvalid = contactEmail.trim() !== '' && !/^\S+@\S+\.\S+$/.test(contactEmail.trim())

  // Resolve favorites server-side so the shortlist never depends on which
  // recommendation batches happen to be loaded.
  async function loadFavorites() {
    const data = await api.getFavoriteItems()
    setFavStrollers(data.strollers)
    setFavAccessories(data.accessories)
  }

  useEffect(() => {
    loadFavorites().catch(console.error)
  }, [])

  useEffect(() => () => {
    if (undoTimer.current) clearTimeout(undoTimer.current)
  }, [])

  async function handleConfirm() {
    if (emailInvalid) return
    const result = await api.handoff({
      name: contactName.trim() || undefined,
      surname: contactSurname.trim() || undefined,
      email: contactEmail.trim() || undefined,
    })
    setHandoff(result.session_code, result.handoff_at)
    setStatus('handoff')
    if (source === 'store') navigate('/handoff')
    else navigate('/complete')
  }

  async function handleRemoveFavorite(id: string, type: 'stroller' | 'accessory') {
    setBusyId(id)
    try {
      const result = await api.toggleFavorite(id, type)
      setFavorites(result.stroller_favorites, result.accessory_favorites)
      await loadFavorites()
      // Offer a brief undo — a tap on the small "Verwijder" button is easy to misfire.
      setUndo({ id, type })
      if (undoTimer.current) clearTimeout(undoTimer.current)
      undoTimer.current = setTimeout(() => setUndo(null), 6000)
    } finally {
      setBusyId(null)
    }
  }

  async function handleUndoRemove() {
    if (!undo) return
    const { id, type } = undo
    setUndo(null)
    if (undoTimer.current) clearTimeout(undoTimer.current)
    const result = await api.toggleFavorite(id, type) // toggling again re-adds it
    setFavorites(result.stroller_favorites, result.accessory_favorites)
    await loadFavorites()
  }

  return (
    <div className="min-h-screen bg-cream text-ink font-sans pb-48">
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
            {favAccessories.length > 0 && (
              <div className="mb-6">
                <h2 className="font-semibold text-ink mb-2">Accessoires</h2>
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
              </div>
            )}
          </>
        )}

        <section className="mt-8 border-t border-muted pt-6">
          <h2 className="font-semibold text-ink mb-1">Jullie gegevens (optioneel)</h2>
          <p className="text-ink/60 text-sm mb-4">
            Laat eventueel je naam en e-mailadres achter. Niet verplicht — je kan ook
            gewoon de sessiecode gebruiken.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
              placeholder="Voornaam"
              autoComplete="given-name"
              className="border-2 border-muted rounded-card px-3 py-2 bg-white text-sm outline-none focus:border-brand"
            />
            <input
              value={contactSurname}
              onChange={(e) => setContactSurname(e.target.value)}
              placeholder="Achternaam"
              autoComplete="family-name"
              className="border-2 border-muted rounded-card px-3 py-2 bg-white text-sm outline-none focus:border-brand"
            />
            <input
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="E-mailadres"
              autoComplete="email"
              className="sm:col-span-2 border-2 border-muted rounded-card px-3 py-2 bg-white text-sm outline-none focus:border-brand"
            />
          </div>
          {emailInvalid && (
            <p className="text-danger text-sm mt-2">Vul een geldig e-mailadres in of laat het veld leeg.</p>
          )}
        </section>
      </div>

      <div className="fixed bottom-0 left-0 right-0 bg-cream border-t border-muted p-4">
        <div className="max-w-lg mx-auto flex flex-col gap-3">
          {undo && (
            <div className="flex items-center justify-between gap-3 text-sm bg-white border border-muted rounded-card px-3 py-2">
              <span className="text-ink/70">Favoriet verwijderd.</span>
              <button onClick={handleUndoRemove} className="text-brand font-medium underline">
                Ongedaan maken
              </button>
            </div>
          )}
          {!hasFavorites && (
            <p className="text-center text-sm text-ink/70">Bewaar minstens één favoriet om te delen.</p>
          )}
          <button
            onClick={handleConfirm}
            disabled={!hasFavorites || emailInvalid}
            className="w-full bg-brand text-white rounded-btn px-6 py-3 font-medium disabled:opacity-50"
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
    </div>
  )
}
