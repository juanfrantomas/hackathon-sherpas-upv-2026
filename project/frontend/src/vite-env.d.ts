/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Base URL of the Sherpas AI backend.
   *
   * When this is unset the mentor runs fully scripted, exactly as the
   * prototype did, and the app never makes a network request.
   */
  readonly VITE_MENTOR_API_URL?: string
  readonly VITE_MILESTONES_API_URL?: string
  /**
   * What to do when the live mentor cannot be reached:
   * `scripted` falls back to the scripted answer, `error` shows the
   * mentor's error state.
   */
  readonly VITE_MENTOR_FALLBACK?: 'scripted' | 'error'
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
