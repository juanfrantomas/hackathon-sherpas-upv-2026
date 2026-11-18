/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the backend (FastAPI, `project/backend`). */
  readonly VITE_BACKEND_API_URL?: string
  /** Alias of `VITE_BACKEND_API_URL`. */
  readonly VITE_MILESTONES_API_URL?: string
  /** Alias of `VITE_BACKEND_API_URL`. */
  readonly VITE_MENTOR_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
