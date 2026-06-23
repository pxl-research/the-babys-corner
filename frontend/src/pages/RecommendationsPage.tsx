import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import ProductCard from '../components/ProductCard'
import ProductModal from '../components/ProductModal'
import AccessoryModal from '../components/AccessoryModal'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'
import type { StrollerItem, AccessoryItem } from '../api/client'

export default function RecommendationsPage() {
  const navigate = useNavigate()
  const {
    recommendations, addBatch, currentBatch,
    strollerFavorites, accessoryFavorites, setFavorites,
    favoritesAdaptationActive, setFavoritesAdaptation,
    recoTiers, setRecoTiers,
    tagMatchMode, droppedTagCount,
  } = useSessionStore()

  const [loading, setLoading] = useState(false)
  const [exhausted, setExhausted] = useState(false)
  const [selectedStroller, setSelectedStroller] = useState<StrollerItem | null>(null)
  const [selectedAccessory, setSelectedAccessory] = useState<AccessoryItem | null>(null)
  const [returnToStroller, setReturnToStroller] = useState<StrollerItem | null>(null)

  // Load batch 1 on mount
  useEffect(() => {
    if (recommendations.length === 0) loadNextBatch()
  }, [])

  async function loadNextBatch() {
    if (loading || exhausted) return
    setLoading(true)
    try {
      const batch = await api.getRecommendations(currentBatch + 1)
      if (batch.products.length === 0) {
        setExhausted(true)
        return
      }
      addBatch(batch.products)
      if (batch.tiers?.length) setRecoTiers(batch.tiers)
      if (batch.favorites_adaptation_active) setFavoritesAdaptation(true)
      // A short batch means the assortment is spent — no more pages after this one.
      if (batch.products.length < 3) setExhausted(true)
    } finally {
      setLoading(false)
    }
  }

  async function handleToggleFavorite(id: string, type: 'stroller' | 'accessory') {
    const result = await api.toggleFavorite(id, type)
    setFavorites(result.stroller_favorites, result.accessory_favorites)
  }

  const allProducts = recommendations.flat()

  // Segment the flat product list into exact→relaxed tiers using the boundaries from the
  // backend. Without tiers (profile-only flow), render a single unlabeled section.
  const sections =
    recoTiers.length > 0
      ? recoTiers
          .map((tier, i) => ({
            label: tier.label,
            products: allProducts.slice(
              tier.start_index,
              recoTiers[i + 1]?.start_index ?? allProducts.length
            ),
          }))
          .filter((section) => section.products.length > 0)
      : [{ label: '', products: allProducts }]

  return (
    <div className="min-h-screen bg-cream text-ink font-sans pb-24">
      <Header />
      <div className="max-w-4xl mx-auto px-4 py-6">
        <h1 className="font-display text-2xl font-bold text-ink mb-1">Onze aanbevelingen voor jullie</h1>
        <p className="text-ink/70 mb-4">
          Op basis van jullie antwoorden hebben we de beste matches voor jullie geselecteerd.
        </p>
        {favoritesAdaptationActive && (
          <p className="text-brand-dark text-sm mb-4">We houden rekening met jullie favorieten.</p>
        )}
        {tagMatchMode === 'partial' && droppedTagCount > 0 && (
          <p className="text-ink/70 text-sm mb-4">
            Niet al jullie wensen waren samen te combineren. Naast de beste matches tonen
            we daarom ook ruimere opties die goed bij jullie passen.
          </p>
        )}
        {sections.map((section, i) => (
          <section key={section.label || i} className="mt-6">
            {section.label && (
              <h2 className="font-display text-lg font-bold text-ink mb-3">{section.label}</h2>
            )}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {section.products.map((stroller) => (
                <ProductCard
                  key={stroller.id}
                  stroller={stroller}
                  isFavorited={strollerFavorites.includes(stroller.id)}
                  onToggleFavorite={() => handleToggleFavorite(stroller.id, 'stroller')}
                  onClick={() => setSelectedStroller(stroller)}
                />
              ))}
            </div>
          </section>
        ))}
        {!loading && !exhausted && (
          <div className="mt-6 text-center">
            <button
              onClick={loadNextBatch}
              className="border border-brand text-brand-dark rounded-btn px-6 py-3 font-medium"
            >
              Bekijk meer opties
            </button>
          </div>
        )}
        {!loading && exhausted && (
          <p className="text-center text-ink/70 mt-6">Alle opties getoond.</p>
        )}
        {loading && <p className="text-center text-ink/70 mt-6">Laden…</p>}
      </div>

      <div className="fixed bottom-0 left-0 right-0 bg-cream border-t border-muted p-4">
        <button
          onClick={() => navigate('/shortlist')}
          className="w-full max-w-lg mx-auto block bg-brand text-ink rounded-btn px-6 py-3 font-medium text-center"
        >
          Naar mijn favorieten
        </button>
      </div>

      <ProductModal
        stroller={selectedStroller}
        isFavorited={selectedStroller ? strollerFavorites.includes(selectedStroller.id) : false}
        onToggleFavorite={(id) => handleToggleFavorite(id, 'stroller')}
        onAccessoryClick={(acc) => {
          if (selectedStroller) setReturnToStroller(selectedStroller)
          setSelectedStroller(null)
          setSelectedAccessory(acc)
        }}
        onClose={() => setSelectedStroller(null)}
      />

      <AccessoryModal
        accessory={selectedAccessory}
        isFavorited={selectedAccessory ? accessoryFavorites.includes(selectedAccessory.id) : false}
        onToggleFavorite={() => selectedAccessory && handleToggleFavorite(selectedAccessory.id, 'accessory')}
        backToStroller={Boolean(returnToStroller)}
        onClose={() => {
          setSelectedAccessory(null)
          if (returnToStroller) {
            setSelectedStroller(returnToStroller)
            setReturnToStroller(null)
          }
        }}
      />
    </div>
  )
}
