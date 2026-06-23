import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Header from '../components/Header'
import ProgressDots from '../components/ProgressDots'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'
import { INTRO_STEP, OVERVIEW_STEP, FIRST_TAG_STEP, TOTAL_STEPS } from '../config/flowSteps'

export default function CategoryIntroPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { categoryConfig, setCategoryConfig, activeCategory, startCategory } = useSessionStore()

  useEffect(() => {
    if (!categoryConfig) {
      api.getCategoryConfig().then(setCategoryConfig).catch(console.error)
    }
  }, [categoryConfig, setCategoryConfig])

  useEffect(() => {
    if (!categoryConfig || !id) return

    const cat = categoryConfig.categories.find((c) => c.id === id)
    if (!cat || cat.status !== 'ai') {
      navigate('/categories', { replace: true })
      return
    }

    // Initialize active category if not already set to this id.
    // Guard prevents resetting answers when navigating back from first tag step.
    if (activeCategory !== id) {
      api.selectCategory(id)
        .then(() => startCategory(id))
        .catch(console.error)
    }
  }, [categoryConfig, id, activeCategory, startCategory, navigate])

  if (!categoryConfig) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <p className="text-ink/70">Laden…</p>
      </div>
    )
  }

  const cat = categoryConfig.categories.find((c) => c.id === id)
  if (!cat || cat.status !== 'ai') return null

  return (
    <div className="min-h-screen bg-cream text-ink font-sans">
      <Header />
      <div className="max-w-lg mx-auto px-6 py-8">
        <ProgressDots total={TOTAL_STEPS} current={INTRO_STEP} filled={OVERVIEW_STEP} />
        <p className="text-ink/80 mt-6 mb-8">{cat.intro}</p>
        <div className="flex flex-col gap-3">
          <button
            onClick={() => navigate('/quiz/' + FIRST_TAG_STEP)}
            className="bg-brand text-ink rounded-btn px-6 py-3 font-medium"
          >
            Verder
          </button>
          <button
            onClick={() => navigate('/categories')}
            className="border border-brand text-brand-dark rounded-btn px-6 py-3 font-medium"
          >
            Terug
          </button>
        </div>
      </div>
    </div>
  )
}
