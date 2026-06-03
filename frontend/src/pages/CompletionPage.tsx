import Header from '../components/Header'
import { useSessionStore } from '../store/sessionStore'

export default function CompletionPage() {
  const {
    sessionCode, handoffAt,
    recommendations, strollerFavorites, accessoryFavorites, optionalNote,
  } = useSessionStore()

  const allProducts = recommendations.flat()
  const accessoryMap = new Map(
    allProducts.flatMap((stroller) => stroller.cross_sell_items.map((accessory) => [accessory.id, accessory]))
  )
  const favoriteStrollers = allProducts.filter((stroller) => strollerFavorites.includes(stroller.id))
  const favoriteAccessories = accessoryFavorites
    .map((id) => accessoryMap.get(id))
    .filter((accessory): accessory is NonNullable<typeof accessory> => Boolean(accessory))

  return (
    <div className="min-h-screen bg-cream text-ink font-sans">
      <Header />
      <div className="max-w-lg mx-auto px-6 py-12">
        <div className="flex flex-col items-center text-center gap-6">
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
        </div>

        <div className="mt-10 space-y-8 text-left">
          {favoriteStrollers.length > 0 || favoriteAccessories.length > 0 ? (
            <section>
              <h2 className="font-semibold text-ink mb-3">Jullie favorieten</h2>
              {favoriteStrollers.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-ink/70 mb-2">Kinderwagens</h3>
                  <ul className="space-y-2">
                    {favoriteStrollers.map((stroller) => (
                      <li key={stroller.id} className="rounded-card border border-muted bg-cream p-3">
                        <p className="font-medium text-ink">{stroller.name}</p>
                        <p className="text-sm text-ink/60">{stroller.brand}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {favoriteAccessories.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-ink/70 mb-2">Accessoires</h3>
                  <ul className="space-y-2">
                    {favoriteAccessories.map((accessory) => (
                      <li key={accessory.id} className="rounded-card border border-muted bg-cream p-3">
                        <p className="font-medium text-ink">{accessory.name}</p>
                        <p className="text-sm text-ink/60">{accessory.brand}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          ) : null}

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
