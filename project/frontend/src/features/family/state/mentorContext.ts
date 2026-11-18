import { createContext } from 'react'
import type { RealtimeVoiceValue } from '../hooks/useRealtimeVoice'

/** The live conversation with the mentor, plus the actions the screen needs. */
export interface MentorSession extends RealtimeVoiceValue {
  /** Opens the live voice, greeting the topic when the household came from one. */
  start: () => void
  /** Sends a question; opens the live voice first when it is not open yet. */
  ask: (question: string) => void
}

export const MentorContext = createContext<MentorSession | null>(null)
