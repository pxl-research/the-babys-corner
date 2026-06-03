import { useEffect, useRef } from 'react'
import { api } from '../api/client'

const INACTIVITY_TIMEOUT_MS = 10 * 60 * 1000

// In-store kiosks must reset to the welcome screen when a customer walks away, so the
// next customer never resumes a stranger's session. No-op for the at-home flow.
export function useInactivityReset(source: string, timeoutMs = INACTIVITY_TIMEOUT_MS) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (source !== 'store') return

    const abandon = () => {
      api.abandon().catch(() => {})
      window.location.href = '/'
    }
    const reset = () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(abandon, timeoutMs)
    }

    const events = ['click', 'touchstart', 'keydown']
    events.forEach((e) => window.addEventListener(e, reset))
    reset()
    return () => {
      events.forEach((e) => window.removeEventListener(e, reset))
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [source, timeoutMs])
}
