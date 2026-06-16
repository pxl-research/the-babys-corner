import { useEffect, useState } from 'react'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import type { StrollerItem, AccessoryItem, VariantSummary } from '../api/client'
import AccessoryCarouselCard from './AccessoryCarouselCard'
import Markdown from './Markdown'

interface Props {
  stroller: StrollerItem | null
  isFavorited: boolean
  onToggleFavorite: (id: string) => void
  onAccessoryClick: (acc: AccessoryItem) => void
  onClose: () => void
}

export default function ProductModal({
  stroller, isFavorited, onToggleFavorite, onAccessoryClick, onClose,
}: Props) {
  const reduceMotion = useReducedMotion()
  // Tracks the active colour variant within the modal. Resets when a new product opens.
  const [activeVariant, setActiveVariant] = useState<VariantSummary | null>(null)
  useEffect(() => { setActiveVariant(null) }, [stroller?.id])

  // Overlay the representative stroller with the selected variant's display fields.
  const displayName = activeVariant?.name ?? stroller?.name ?? ''
  const displayImage = activeVariant?.image_url ?? stroller?.image_url ?? ''
  const displayPrice = activeVariant?.price ?? stroller?.price ?? 0
  const displayAvailability = activeVariant?.availability ?? stroller?.availability ?? ''
  const activeId = activeVariant?.id ?? stroller?.id ?? ''

  const descriptionText = stroller?.formatted_description ?? stroller?.description ?? ''
  const variants = stroller?.variant_summaries ?? []
  const hasVariants = variants.length > 1

  // Close on Escape so keyboard users aren't trapped (backdrop click already closes).
  useEffect(() => {
    if (!stroller) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [stroller, onClose])

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
              {displayImage && (
                <img src={displayImage} alt={displayName} className="w-full h-56 object-contain mb-4 rounded-card" />
              )}
              <p className="text-xs font-semibold tracking-widest uppercase text-ink/70 mb-1">{stroller.brand}</p>
              <h2 className="font-display text-2xl font-bold text-ink mb-1">{displayName}</h2>
              <p className="text-xl font-medium text-ink mb-1">€ {displayPrice.toFixed(2)}</p>
              <p className="text-sm text-ink/60 mb-3">{displayAvailability}</p>
              {hasVariants && (
                <div className="mb-4">
                  <p className="text-xs font-semibold text-ink/60 uppercase tracking-widest mb-2">Kleur</p>
                  <div className="flex gap-2 flex-wrap">
                    {variants.map((v) => (
                      <button
                        key={v.id}
                        onClick={() => setActiveVariant(v.id === activeId && activeVariant ? null : v)}
                        className={`flex flex-col items-center gap-1 rounded-card border-2 p-1 transition-colors ${
                          v.id === activeId
                            ? 'border-brand-dark'
                            : 'border-muted/50 hover:border-muted'
                        } ${!v.is_available ? 'opacity-50' : ''}`}
                        title={v.colour_label + (!v.is_available ? ' (niet op voorraad)' : '')}
                      >
                        <img src={v.image_url} alt={v.colour_label} className="w-14 h-14 object-contain rounded" />
                        <span className="text-[10px] text-ink/70 leading-tight text-center max-w-[56px] line-clamp-2">
                          {v.colour_label}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <Markdown text={descriptionText} className="text-ink/80 mb-4" />
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
                onClick={() => onToggleFavorite(activeId)}
                className="w-full bg-brand text-ink rounded-btn px-6 py-3 font-medium"
              >
                {isFavorited ? '♥ In favorieten' : 'Voeg toe aan favorieten'}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
