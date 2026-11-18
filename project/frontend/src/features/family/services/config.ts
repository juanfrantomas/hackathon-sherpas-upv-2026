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


/** The first access to a case may generate its milestones with the AI. */
export const MILESTONES_TIMEOUT_MS = 60_000

/** How long the client waits for the pillars (the copy is written by the AI). */
export const PILLARS_TIMEOUT_MS = 90_000
