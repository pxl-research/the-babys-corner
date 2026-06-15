import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSessionStore } from '../store/sessionStore'
import { api } from '../api/client'

export default function Header() {
  const navigate = useNavigate()
  const { reset, sessionId } = useSessionStore()
  const [confirmOpen, setConfirmOpen] = useState(false)

  function handleLogoClick() {
    if (!sessionId) {
      navigate('/')
      return
    }
    setConfirmOpen(true)
  }

  function confirmRestart() {
    api.abandon().catch(() => {})
    reset()
    setConfirmOpen(false)
    navigate('/')
  }

  return (
    <>
      <header className="bg-cream border-b border-muted py-4">
        <div className="max-w-2xl mx-auto px-4 flex justify-center">
          <button onClick={handleLogoClick} className="focus:outline-none" aria-label="Opnieuw beginnen">
            <img src="/logo.png" alt="The Baby's Corner" className="max-h-[4.5rem] object-contain cursor-pointer hover:opacity-75 transition-opacity" />
          </button>
        </div>
      </header>

      {confirmOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-6"
          role="dialog"
          aria-modal="true"
          aria-labelledby="restart-title"
          onClick={() => setConfirmOpen(false)}
        >
          <div
            className="bg-cream rounded-card max-w-sm w-full p-6 text-center shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="restart-title" className="font-display text-xl font-bold text-ink mb-2">
              Opnieuw beginnen?
            </h2>
            <p className="text-ink/70 text-sm mb-6">Alle antwoorden en favorieten worden gewist.</p>
            <div className="flex flex-col gap-3">
              <button
                onClick={confirmRestart}
                className="bg-brand text-white rounded-btn px-6 py-3 font-medium"
              >
                Ja, opnieuw beginnen
              </button>
              <button
                onClick={() => setConfirmOpen(false)}
                className="border border-brand text-brand rounded-btn px-6 py-3 font-medium"
              >
                Annuleren
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
