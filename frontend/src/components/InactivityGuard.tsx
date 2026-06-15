import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'

const TIMEOUT_MS = 10 * 60 * 1000
const WARN_MS = 60 * 1000 // show the warning this long before resetting

// Routes where an idle kiosk should reset to welcome. Welcome/transition and the
// staff-facing handoff/completion screens are intentionally excluded.
const GUARDED = ['/quiz', '/recommendations', '/shortlist']

// In-store kiosks reset to the welcome screen when a customer walks away, so the next
// customer never resumes a stranger's session. Before wiping, a countdown warning lets a
// customer who merely paused stay. No-op for the at-home flow.
export default function InactivityGuard() {
  const { source } = useSessionStore()
  const { pathname } = useLocation()
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null) // non-null => warning shown
  const resetRef = useRef<() => void>(() => {})

  const armed = source === 'store' && GUARDED.some((p) => pathname.startsWith(p))

  useEffect(() => {
    if (!armed) {
      setSecondsLeft(null)
      return
    }

    let idleTimer: ReturnType<typeof setTimeout> | null = null
    let countdown: ReturnType<typeof setInterval> | null = null

    const clearAll = () => {
      if (idleTimer) clearTimeout(idleTimer)
      if (countdown) clearInterval(countdown)
    }

    const abandon = () => {
      clearAll()
      api.abandon().catch(() => {})
      window.location.href = '/'
    }

    const startWarning = () => {
      let left = Math.floor(WARN_MS / 1000)
      setSecondsLeft(left)
      countdown = setInterval(() => {
        left -= 1
        if (left <= 0) {
          abandon()
          return
        }
        setSecondsLeft(left)
      }, 1000)
    }

    const schedule = () => {
      clearAll()
      setSecondsLeft(null)
      idleTimer = setTimeout(startWarning, TIMEOUT_MS - WARN_MS)
    }
    resetRef.current = schedule

    const events = ['click', 'touchstart', 'keydown']
    events.forEach((e) => window.addEventListener(e, schedule))
    schedule()
    return () => {
      events.forEach((e) => window.removeEventListener(e, schedule))
      clearAll()
    }
  }, [armed, pathname])

  if (secondsLeft === null) return null

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 px-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="idle-title"
    >
      <div className="bg-cream rounded-card max-w-sm w-full p-6 text-center shadow-xl">
        <h2 id="idle-title" className="font-display text-xl font-bold text-ink mb-2">Ben je er nog?</h2>
        <p className="text-ink/70 text-sm mb-6">
          We sluiten deze sessie over {secondsLeft} seconde{secondsLeft === 1 ? '' : 'n'} en
          beginnen opnieuw voor de volgende klant.
        </p>
        <button
          onClick={() => resetRef.current()}
          className="w-full bg-brand text-white rounded-btn px-6 py-3 font-medium"
        >
          Ja, ik ben er nog
        </button>
      </div>
    </div>
  )
}
