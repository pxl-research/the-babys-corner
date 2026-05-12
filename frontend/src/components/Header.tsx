import { useNavigate } from 'react-router-dom'
import { useSessionStore } from '../store/sessionStore'
import { api } from '../api/client'

export default function Header() {
  const navigate = useNavigate()
  const { reset, sessionId } = useSessionStore()

  function handleLogoClick() {
    if (!sessionId) {
      navigate('/')
      return
    }
    if (!window.confirm('Opnieuw beginnen? Alle antwoorden worden gewist.')) return
    api.abandon().catch(() => {})
    reset()
    navigate('/')
  }

  return (
    <header className="bg-cream border-b border-muted py-4">
      <div className="max-w-2xl mx-auto px-4 flex justify-center">
        <button onClick={handleLogoClick} className="focus:outline-none" aria-label="Opnieuw beginnen">
          <img src="/logo.png" alt="The Baby's Corner" className="max-h-[4.5rem] object-contain cursor-pointer hover:opacity-75 transition-opacity" />
        </button>
      </div>
    </header>
  )
}
