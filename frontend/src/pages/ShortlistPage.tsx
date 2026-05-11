import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'

export default function ShortlistPage() {
  const navigate = useNavigate()
  const {
    source, strollerFavorites, accessoryFavorites, recommendations, setHandoff, setEmailStatus, setStatus,
  } = useSessionStore()

  const allStrollers = recommendations.flat()
  const favStrollers = allStrollers.filter((s) => strollerFavorites.includes(s.id))

  async function handleConfirm() {
    const result = await api.handoff()
    setHandoff(result.session_code, result.handoff_at)
    setEmailStatus(result.email_status as 'pending')
    setStatus('handoff')
    if (source === 'store') navigate('/handoff')
    else navigate('/complete')
  }

  return (
    <div className="min-h-screen bg-cream text-ink font-sans pb-24">
      <Header />
      <div className="max-w-lg mx-auto px-6 py-8">
        <h1 className="font-display text-2xl font-bold text-ink mb-1">Jullie favorieten</h1>
        <p className="text-ink/60 mb-6">Deze items hebben jullie bewaard.</p>

        {strollerFavorites.length === 0 && accessoryFavorites.length === 0 ? (
          <p className="text-ink/50 italic">Jullie hebben nog geen favorieten bewaard.</p>
        ) : (
          <>
            {favStrollers.length > 0 && (
              <div className="mb-6">
                <h2 className="font-semibold text-ink mb-2">Kinderwagens</h2>
                <ul className="space-y-2">
                  {favStrollers.map((s) => (
                    <li key={s.id} className="bg-white rounded-card p-3 border border-muted">
                      <p className="font-medium text-ink">{s.name}</p>
                      <p className="text-ink/60 text-sm">€ {s.price.toFixed(2)}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {accessoryFavorites.length > 0 && (
              <div className="mb-6">
                <h2 className="font-semibold text-ink mb-2">Accessoires</h2>
                <ul className="space-y-1">
                  {accessoryFavorites.map((id) => (
                    <li key={id} className="text-ink/70 text-sm">{id}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>

      <div className="fixed bottom-0 left-0 right-0 bg-cream border-t border-muted p-4 flex flex-col gap-3 max-w-lg mx-auto">
        <button
          onClick={handleConfirm}
          className="w-full bg-brand text-white rounded-btn px-6 py-3 font-medium"
        >
          Deel met medewerker
        </button>
        <button
          onClick={() => navigate('/recommendations')}
          className="w-full border border-brand text-brand rounded-btn px-6 py-3 font-medium"
        >
          Terug naar aanbevelingen
        </button>
      </div>
    </div>
  )
}
