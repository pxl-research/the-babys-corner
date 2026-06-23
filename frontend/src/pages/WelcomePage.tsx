import { useNavigate, useSearchParams } from 'react-router-dom'
import { useEffect } from 'react'
import Header from '../components/Header'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'

export default function WelcomePage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { setSource, setSession, reset } = useSessionStore()
  const src = params.get('source') === 'store' ? 'store' : 'home'

  useEffect(() => {
    setSource(src)
  }, [src, setSource])

  async function handleStart() {
    reset()
    setSource(src)
    const data = await api.createSession(src)
    setSession(data.session_id, data.session_code)
    navigate('/quiz/1')
  }

  return (
    <div className="min-h-screen bg-cream text-ink font-sans">
      <Header />
      <main className="max-w-lg mx-auto px-6 py-12 flex flex-col items-center text-center gap-6">
        <h1 className="font-display text-3xl md:text-4xl font-bold text-ink leading-tight">
          Welkom bij the baby's corner!
        </h1>
        <p className="text-ink/70 text-lg">
          De voorbereiding op je baby is een spannende tijd, vol dromen en keuzes. Onze
          digitale babychecklist begeleidt je stap voor stap: van kinderwagen tot
          babykamer, afgestemd op wat écht bij jullie past. Ik start met twee korte
          vragen, zodat ik je meteen de juiste richting kan wijzen.
        </p>
        <button
          onClick={handleStart}
          className="bg-brand text-ink rounded-btn px-8 py-3 font-medium text-lg mt-4"
        >
          Start
        </button>
      </main>
    </div>
  )
}
