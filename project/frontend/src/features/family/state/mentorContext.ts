import { createContext } from 'react'
import type { VoiceState } from '../types'

export interface MentorSession {
  /** The question currently being asked. */
  question: string
  /** The answer being spoken: the live one, or the scripted fallback. */
  answer: string
  /** The audio of the answer, when the backend sent one. */
  audio: string | null
  /** Whether the current answer came from the live mentor. */
  live: boolean
  /** Whether the app is configured to use the live mentor at all. */
  liveEnabled: boolean
  /** Whether a request to the mentor is in flight. */
  pending: boolean
  /** Starts a question. Defaults to the household's scripted question. */
  ask: (question?: string) => void
  /** Advances the conversation, as the microphone button does. */
  advance: () => void
  /** Mutes or unmutes the microphone. */
  setMuted: (muted: boolean) => void
  /** Asks the current question again. */
  retry: () => void
  /** Ends the session and returns to the ready state. */
  end: () => void
}

export const MentorContext = createContext<MentorSession | null>(null)

export type { VoiceState }
