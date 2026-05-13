import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import type { StrollerItem, AccessoryItem } from '../api/client'
import AccessoryCarouselCard from './AccessoryCarouselCard'

interface Props {
  stroller: StrollerItem | null
  isFavorited: boolean
  onToggleFavorite: () => void
  onAccessoryClick: (acc: AccessoryItem) => void
  onClose: () => void
}

export default function ProductModal({
  stroller, isFavorited, onToggleFavorite, onAccessoryClick, onClose,
}: Props) {
  const reduceMotion = useReducedMotion()
  const descriptionText = stroller?.formatted_description ?? stroller?.description ?? ''

  function isRedundantKeyFeatures(features: string, description: string) {
    const f = features.trim()
    const d = description.trim()
    if (!f || !d) return false
    const headingSignals = ['belangrijkste kenmerken', 'kenmerken', 'specificaties', 'technische specificaties']
    const hasHeadingInDescription = headingSignals.some((h) => d.toLowerCase().includes(h))
    if (!hasHeadingInDescription) return false

    const firstFeatureLine = f
      .split('\n')
      .map((line) => line.replace(/^[•\-*]\s*/, '').trim())
      .find(Boolean)
    if (!firstFeatureLine) return false

    const normalizedNeedle = firstFeatureLine.toLowerCase().replace(/[^a-z0-9]+/g, '')
    const normalizedHaystack = d.toLowerCase().replace(/[^a-z0-9]+/g, '')
    return normalizedHaystack.includes(normalizedNeedle)
  }

  const showKeyFeatures = Boolean(
    stroller?.key_features && !isRedundantKeyFeatures(stroller.key_features, descriptionText)
  )

  return (
    <AnimatePresence>
      {stroller && (
        <>
          <motion.div
            className="fixed inset-0 bg-black/40 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.2 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed bottom-0 left-0 right-0 z-50 bg-cream rounded-t-2xl shadow-xl max-h-[90vh] overflow-y-auto"
            initial={reduceMotion ? {} : { y: '100%' }}
            animate={{ y: 0 }}
            exit={reduceMotion ? {} : { y: '100%' }}
            transition={{ duration: reduceMotion ? 0 : 0.3, ease: 'easeOut' }}
          >
            <div className="w-10 h-1 bg-muted rounded-full mx-auto mt-2" />
            <div className="p-6">
              <div className="flex justify-end mb-2">
                <button
                  onClick={onClose}
                  className="text-sm text-ink/70 border border-muted rounded-btn px-3 py-1"
                >
                  Sluiten
                </button>
              </div>
              {stroller.image_url && (
                <img src={stroller.image_url} alt={stroller.name} className="w-full h-56 object-contain mb-4 rounded-card" />
              )}
              <p className="text-xs font-semibold tracking-widest uppercase text-ink/60 mb-1">{stroller.brand}</p>
              <h2 className="font-display text-2xl font-bold text-ink mb-1">{stroller.name}</h2>
              <p className="text-xl font-medium text-ink mb-2">€ {stroller.price.toFixed(2)}</p>
              {!stroller.is_available && (
                <span className="bg-muted/60 text-ink/60 text-xs px-2 py-0.5 rounded-full mb-2 inline-block">
                  Niet beschikbaar
                </span>
              )}
              <p className="text-ink/80 mb-4 whitespace-pre-line">{descriptionText}</p>
              {showKeyFeatures && (
                <div className="bg-brand/10 rounded-card p-4 mb-4">
                  <p className="font-semibold text-ink mb-1 text-sm">Kenmerken</p>
                  <p className="text-ink/80 text-sm whitespace-pre-line">{stroller.key_features}</p>
                </div>
              )}
              {stroller.cross_sell_items.length > 0 && (
                <div className="mb-4">
                  <p className="font-semibold text-ink mb-2 text-sm">Passende accessoires</p>
                  <div className="flex gap-3 overflow-x-auto pb-1">
                    {stroller.cross_sell_items.map((acc) => (
                      <AccessoryCarouselCard key={acc.id} accessory={acc} onClick={() => onAccessoryClick(acc)} />
                    ))}
                  </div>
                </div>
              )}
              <button
                onClick={onToggleFavorite}
                className="w-full bg-brand text-white rounded-btn px-6 py-3 font-medium"
              >
                {isFavorited ? '♥ In mijn lijst' : 'Voeg toe aan mijn lijst'}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
