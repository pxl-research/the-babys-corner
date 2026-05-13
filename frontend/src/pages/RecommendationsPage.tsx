import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import ProductCard from '../components/ProductCard'
import ProductModal from '../components/ProductModal'
import AccessoryModal from '../components/AccessoryModal'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'
import type { StrollerItem, AccessoryItem } from '../api/client'

const INACTIVITY_TIMEOUT_MS = 10 * 60 * 1000

export default function RecommendationsPage() {
  const navigate = useNavigate()
  const {
    source, recommendations, addBatch, currentBatch,
    strollerFavorites, accessoryFavorites, setFavorites,
    favoritesAdaptationActive, setFavoritesAdaptation,
  } = useSessionStore()

  const [loading, setLoading] = useState(false)
  const [selectedStroller, setSelectedStroller] = useState<StrollerItem | null>(null)
  const [selectedAccessory, setSelectedAccessory] = useState<AccessoryItem | null>(null)
  const [returnToStroller, setReturnToStroller] = useState<StrollerItem | null>(null)
  const inactivityRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Load batch 1 on mount
  useEffect(() => {
    if (recommendations.length === 0) loadNextBatch()
  }, [])

  // In-store inactivity timer
  useEffect(() => {
    if (source !== 'store') return
    const reset = () => {
      if (inactivityRef.current) clearTimeout(inactivityRef.current)
      inactivityRef.current = setTimeout(handleAbandon, INACTIVITY_TIMEOUT_MS)
    }
    const events = ['click', 'touchstart', 'keydown']
    events.forEach((e) => window.addEventListener(e, reset))
    reset()
    return () => {
      events.forEach((e) => window.removeEventListener(e, reset))
      if (inactivityRef.current) clearTimeout(inactivityRef.current)
    }
  }, [source])

  async function loadNextBatch() {
    if (loading) return
    setLoading(true)
    try {
      const batch = await api.getRecommendations(currentBatch + 1)
      addBatch(batch.products)
      if (batch.favorites_adaptation_active) setFavoritesAdaptation(true)
    } finally {
      setLoading(false)
    }
  }

  async function handleToggleFavorite(id: string, type: 'stroller' | 'accessory') {
    const result = await api.toggleFavorite(id, type)
    setFavorites(result.stroller_favorites, result.accessory_favorites)
  }

  async function handleAbandon() {
    await api.abandon().catch(() => {})
    window.location.href = '/'
  }

  const allProducts = recommendations.flat()

  return (
    <div className="min-h-screen bg-cream text-ink font-sans pb-24">
      <Header />
      <div className="max-w-4xl mx-auto px-4 py-6">
        <h1 className="font-display text-2xl font-bold text-ink mb-2">Onze aanbevelingen voor jullie</h1>
        {favoritesAdaptationActive && (
          <p className="text-brand text-sm mb-4">We houden rekening met jullie favorieten.</p>
        )}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          {allProducts.map((stroller) => (
            <ProductCard
              key={stroller.id}
              stroller={stroller}
              isFavorited={strollerFavorites.includes(stroller.id)}
              onToggleFavorite={() => handleToggleFavorite(stroller.id, 'stroller')}
              onClick={() => setSelectedStroller(stroller)}
            />
          ))}
        </div>
        {!loading && (
          <div className="mt-6 text-center">
            <button
              onClick={loadNextBatch}
              className="border border-brand text-brand rounded-btn px-6 py-3 font-medium"
            >
              Bekijk meer opties
            </button>
          </div>
        )}
        {loading && <p className="text-center text-ink/50 mt-6">Laden…</p>}
      </div>

      <div className="fixed bottom-0 left-0 right-0 bg-cream border-t border-muted p-4">
        <button
          onClick={() => navigate('/shortlist')}
          className="w-full max-w-lg mx-auto block bg-brand text-white rounded-btn px-6 py-3 font-medium text-center"
        >
          Deel met medewerker
        </button>
      </div>

      <ProductModal
        stroller={selectedStroller}
        isFavorited={selectedStroller ? strollerFavorites.includes(selectedStroller.id) : false}
        onToggleFavorite={() => selectedStroller && handleToggleFavorite(selectedStroller.id, 'stroller')}
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
