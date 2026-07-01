import { useEffect } from 'react'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import type { AccessoryItem } from '../api/client'

interface Props {
  accessory: AccessoryItem | null
  isFavorited: boolean
  onToggleFavorite: () => void
  backToStroller?: boolean
  onClose: () => void
}

export default function AccessoryModal({
  accessory,
  isFavorited,
  onToggleFavorite,
  backToStroller,
  onClose,
}: Props) {
  const reduceMotion = useReducedMotion()
  const canRemove = isFavorited
  const canAdd = !isFavorited

  // Close on Escape so keyboard users aren't trapped (backdrop click already closes).
  useEffect(() => {
    if (!accessory) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [accessory, onClose])

  return (
    <AnimatePresence>
      {accessory && (
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
            className="fixed bottom-0 left-0 right-0 z-50 bg-cream rounded-t-2xl shadow-xl max-h-[85vh] overflow-y-auto"
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
                  {backToStroller ? 'Terug naar kinderwagen' : 'Sluiten'}
                </button>
              </div>
              {accessory.image_url && (
                <img src={accessory.image_url} alt={accessory.name} className="w-full h-48 object-contain mb-4 rounded-card" />
              )}
              <p className="text-xs font-semibold tracking-widest uppercase text-ink/70 mb-1">{accessory.brand}</p>
              {accessory.reason && (
                <span className="bg-brand/10 text-brand-dark text-xs px-2 py-0.5 rounded-full mb-1 inline-block">
                  {accessory.reason}
                </span>
              )}
              <h2 className="font-display text-xl font-bold text-ink mb-1">{accessory.name}</h2>
              <p className="text-lg font-medium text-ink mb-2">€ {accessory.price.toFixed(2)}</p>
              <p className="text-ink/80 mb-6">{accessory.description}</p>
              {accessory.product_url && (
                <a
                  href={accessory.product_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full text-center border border-brand text-brand-dark rounded-btn px-6 py-3 font-medium mb-3"
                >
                  Bekijk op website
                </a>
              )}
              {(canAdd || canRemove) && (
                <button
                  onClick={onToggleFavorite}
                  className="w-full bg-brand text-ink rounded-btn px-6 py-3 font-medium"
                >
                  {isFavorited ? '♥ In favorieten' : 'Voeg toe aan favorieten'}
                </button>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
