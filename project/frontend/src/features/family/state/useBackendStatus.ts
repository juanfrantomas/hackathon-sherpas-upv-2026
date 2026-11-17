import { useEffect, useState } from 'react'
import { MILESTONES_API_URL, MILESTONES_LIVE_ENABLED } from '../services/config'

/** `off` = no backend configured; the app runs on its static demo data. */
export type BackendStatus = 'off' | 'checking' | 'connected' | 'offline'

const POLL_MS = 10_000

/** Polls the backend's health endpoint so the shell can show if it is reachable. */
export function useBackendStatus(): BackendStatus {
  const [status, setStatus] = useState<BackendStatus>(
    MILESTONES_LIVE_ENABLED ? 'checking' : 'off',
  )

  useEffect(() => {
    if (!MILESTONES_LIVE_ENABLED) return
    let cancelled = false

    const check = async () => {
      try {
        const res = await fetch(`${MILESTONES_API_URL}/api/health`, {
          signal: AbortSignal.timeout(4_000),
        })
        if (!cancelled) setStatus(res.ok ? 'connected' : 'offline')
      } catch {
        if (!cancelled) setStatus('offline')
      }
    }

    void check()
    const timer = setInterval(check, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  return status
}
