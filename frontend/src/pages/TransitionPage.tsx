import { useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import Header from '../components/Header'
import { useSessionStore } from '../store/sessionStore'

export default function TransitionPage() {
  const navigate = useNavigate()
  const { transitionPhrase } = useSessionStore()
  const reduceMotion = useReducedMotion()

  const advance = useCallback(() => navigate('/recommendations'), [navigate])

  useEffect(() => {
    const timer = setTimeout(advance, 3000)
    return () => clearTimeout(timer)
  }, [advance])

  return (
    <div className="min-h-screen bg-cream text-ink font-sans flex flex-col">
      <Header />
      <div
        className="flex-1 flex flex-col items-center justify-center px-6 gap-6 cursor-pointer"
        onClick={advance}
        role="button"
        tabIndex={0}
        aria-label="Verder naar aanbevelingen"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') advance()
        }}
      >
        <motion.p
          className="font-display text-2xl md:text-3xl font-bold text-ink text-center max-w-md"
          initial={reduceMotion ? {} : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: reduceMotion ? 0 : 0.4, ease: 'easeOut' }}
        >
          {transitionPhrase}
        </motion.p>
        <p className="text-ink/70 text-sm">Tik om verder te gaan</p>
      </div>
    </div>
  )
}
