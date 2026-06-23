import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import ProgressDots from '../components/ProgressDots'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'
import { OVERVIEW_STEP, TOTAL_STEPS, PROFILE_STEPS } from '../config/flowSteps'

const STATUS_BADGE: Record<string, { emoji: string; label: string }> = {
  ai: { emoji: '✅', label: 'Ik help je kiezen' },
  assortiment: { emoji: '🔗', label: 'Bekijk assortiment' },
  soon: { emoji: '⏳', label: 'Binnenkort beschikbaar' },
}

export default function CategoryOverviewPage() {
  const navigate = useNavigate()
  const { categoryConfig, setCategoryConfig, startCategory, addSelectedCategory } = useSessionStore()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!categoryConfig) {
      api.getCategoryConfig().then(setCategoryConfig).catch(console.error)
    }
  }, [categoryConfig, setCategoryConfig])

  if (!categoryConfig) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <p className="text-ink/70">Laden…</p>
      </div>
    )
  }

  async function handleAiCategory(id: string) {
    setError(null)
    try {
      await api.selectCategory(id)
      startCategory(id)
      navigate('/category/' + id)
    } catch {
      setError('Kon de categorie niet selecteren. Probeer opnieuw.')
    }
  }

  async function handleAssortimentCategory(id: string, url: string) {
    setError(null)
    try {
      await api.selectCategory(id)
      addSelectedCategory(id)
      window.open(url, '_blank', 'noopener')
    } catch {
      setError('Kon de categorie niet selecteren. Probeer opnieuw.')
    }
  }

  return (
    <div className="min-h-screen bg-cream text-ink font-sans pb-12">
      <Header />
      <div className="max-w-2xl mx-auto px-6 py-8">
        <ProgressDots total={TOTAL_STEPS} current={OVERVIEW_STEP} filled={PROFILE_STEPS} />
        <p className="font-display text-xl font-bold text-ink mt-6 mb-6">
          {categoryConfig.overview_intro}
        </p>
        {error && (
          <p className="text-red-600 text-sm mb-4">{error}</p>
        )}
        <div className="grid grid-cols-2 gap-3">
          {categoryConfig.categories.map((cat) => {
            const badge = STATUS_BADGE[cat.status] ?? STATUS_BADGE.soon
            const isSoon = cat.status === 'soon'

            return (
              <div
                key={cat.id}
                className={[
                  'border-2 rounded-card p-4 flex flex-col gap-2 transition-colors',
                  isSoon
                    ? 'border-muted opacity-60 cursor-default'
                    : 'border-muted hover:border-brand/60 cursor-pointer',
                ].join(' ')}
                onClick={
                  isSoon
                    ? undefined
                    : cat.status === 'ai'
                      ? () => handleAiCategory(cat.id)
                      : cat.url
                        ? () => handleAssortimentCategory(cat.id, cat.url!)
                        : undefined
                }
              >
                <span className="font-medium text-ink">{cat.label}</span>
                <span className="text-xs text-ink/70">
                  {badge.emoji} {badge.label}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
