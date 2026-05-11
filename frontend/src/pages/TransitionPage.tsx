import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import Header from '../components/Header'
import { useSessionStore } from '../store/sessionStore'

export default function TransitionPage() {
  const navigate = useNavigate()
  const { transitionPhrase } = useSessionStore()
  const reduceMotion = useReducedMotion()

  useEffect(() => {
    const timer = setTimeout(() => navigate('/recommendations'), 3000)
    return () => clearTimeout(timer)
  }, [navigate])

  return (
    <div className="min-h-screen bg-cream text-ink font-sans flex flex-col">
      <Header />
      <div className="flex-1 flex items-center justify-center px-6">
        <motion.p
          className="font-display text-2xl md:text-3xl font-bold text-ink text-center max-w-md"
          initial={reduceMotion ? {} : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: reduceMotion ? 0 : 0.4, ease: 'easeOut' }}
        >
          {transitionPhrase}
        </motion.p>
      </div>
    </div>
  )
}
