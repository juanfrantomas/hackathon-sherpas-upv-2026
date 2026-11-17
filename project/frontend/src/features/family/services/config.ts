/**
 * Runtime configuration.
 *
 * The application talks to one backend: the Financial Milestones backend in
 * `project/backend`.  The three variables below are aliases of the same
 * address, so a project that already had one of them keeps working.
 */

/** Base URL of the backend (FastAPI). Empty means "static demo data only". */
export const BACKEND_API_URL = (
  import.meta.env.VITE_BACKEND_API_URL ??
  import.meta.env.VITE_MILESTONES_API_URL ??
  import.meta.env.VITE_MENTOR_API_URL ??
  ''
)
  .trim()
  .replace(/\/$/, '')

/** Whether the backend can be reached at all. */
export const BACKEND_LIVE_ENABLED = BACKEND_API_URL.length > 0

/** Alias kept for the screens that talk about the milestones service. */
export const MILESTONES_API_URL = BACKEND_API_URL

/** Alias kept for the screens that talk about the milestones service. */
export const MILESTONES_LIVE_ENABLED = BACKEND_LIVE_ENABLED

/** The address of the live voice channel. */
export const BACKEND_WS_URL = BACKEND_API_URL
  .replace(/^http:/, 'ws:')
  .replace(/^https:/, 'wss:')

/**
 * What to do when the live mentor cannot be reached:
 *   scripted - fall back to the scripted answer and keep the demo working
 *   error    - show the mentor's error state ("Try again" / "Read my plan")
 */
export type MentorFallback = 'scripted' | 'error'

function readFallback(): MentorFallback {
  const value = import.meta.env.VITE_MENTOR_FALLBACK?.trim()
  return value === 'error' ? 'error' : 'scripted'
}

export const MENTOR_FALLBACK = readFallback()

/** Whether the app should try the live mentor. */
export const MENTOR_LIVE_ENABLED = BACKEND_LIVE_ENABLED

/** How long the mentor may take before the request is abandoned. */
export const MENTOR_TIMEOUT_MS = 30_000

/** The minimum time the mentor spends "thinking", so the state is perceivable. */
export const MENTOR_MIN_THINKING_MS = 1_600

/** The first access to a case may generate its milestones with the AI. */
export const MILESTONES_TIMEOUT_MS = 60_000

/** How long the client waits for the pillars (the copy is written by the AI). */
export const PILLARS_TIMEOUT_MS = 90_000
