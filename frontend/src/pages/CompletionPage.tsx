import { useEffect, useState } from 'react'
import Header from '../components/Header'
import { api } from '../api/client'
import type { ShortlistItem } from '../api/client'
import { useSessionStore } from '../store/sessionStore'

function FavoriteList({ title, items }: { title: string; items: ShortlistItem[] }) {
  if (items.length === 0) return null
  return (
    <div className="mb-4">
      <h3 className="text-sm font-medium text-ink/70 mb-2">{title}</h3>
      <ul className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {items.map((item) => (
          <li key={item.id} className="rounded-card border border-muted bg-white p-3 flex flex-col">
            {item.image_url && (
              <img src={item.image_url} alt={item.name} className="w-full h-28 object-contain bg-white mb-2" />
            )}
            <p className="text-[10px] font-semibold tracking-widest uppercase text-ink/70 mb-0.5">{item.brand}</p>
            <p className="text-sm font-medium text-ink leading-snug">{item.name}</p>
            <p className="text-sm text-ink/80 mt-1">€ {item.price.toFixed(2)}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function CompletionPage() {
  const { sessionCode, handoffAt, optionalNote } = useSessionStore()
  const [favStrollers, setFavStrollers] = useState<ShortlistItem[]>([])
  const [favAccessories, setFavAccessories] = useState<ShortlistItem[]>([])

  // Resolve favorites server-side so the takeaway screen never depends on which
  // recommendation batches happen to be loaded client-side.
  useEffect(() => {
    api
      .getFavoriteItems()
      .then((data) => {
        setFavStrollers(data.strollers)
        setFavAccessories(data.accessories)
      })
      .catch(console.error)
  }, [])

  const hasFavorites = favStrollers.length > 0 || favAccessories.length > 0

  return (
    <div className="min-h-screen bg-cream text-ink font-sans">
      <Header />
      <div className="max-w-lg mx-auto px-6 py-12">
        <div className="flex flex-col items-center text-center gap-6">
          <p className="text-ink/70 text-sm font-medium uppercase tracking-widest">Jullie sessiecode</p>
          <div className="font-mono text-4xl font-bold bg-brand/10 text-ink px-8 py-4 rounded-card tracking-widest">
            {sessionCode}
          </div>
          <p className="text-ink/80">Klaar! De medewerker kan jullie profiel ophalen met deze code.</p>
          {handoffAt && (
            <p className="text-ink/70 text-sm">
              Aangemaakt op {new Date(handoffAt).toLocaleString('nl-BE')}
            </p>
          )}
        </div>

        <div className="mt-10 space-y-8 text-left">
          {hasFavorites && (
            <section>
              <h2 className="font-semibold text-ink mb-3">Jullie favorieten</h2>
              <FavoriteList title="Kinderwagens" items={favStrollers} />
              <FavoriteList title="Accessoires" items={favAccessories} />
            </section>
          )}

          {optionalNote.trim() && (
            <section>
              <h2 className="font-semibold text-ink mb-2">Extra info</h2>
              <p className="text-sm text-ink/80">{optionalNote}</p>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
