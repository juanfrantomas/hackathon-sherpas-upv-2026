import type { VoiceState } from '../types'

export interface VoiceStateOption {
  id: VoiceState
  label: string
}

/** The seven voice states the mentor can be in, as shown in the prototype controls. */
export const VOICE_STATES: VoiceStateOption[] = [
  { id: 'ready', label: 'Ready' },
  { id: 'listening', label: 'Listening' },
  { id: 'thinking', label: 'Thinking' },
  { id: 'speaking', label: 'Speaking' },
  { id: 'interrupted', label: 'Interrupted' },
  { id: 'muted', label: 'Muted' },
  { id: 'error', label: 'Unavailable' },
]

/** The sentence shown under the mentor orb in each voice state. */
export const VOICE_STATE_TEXT: Record<VoiceState, string> = {
  ready: 'Tap the microphone and ask anything about your plan.',
  listening: 'Listening…',
  thinking: 'Looking at your plan…',
  speaking: 'Speaking · start talking anytime to interrupt',
  interrupted: 'Paused. Go ahead, I’m listening.',
  muted: 'Your microphone is muted. The mentor can’t hear you.',
  error: 'Voice is unavailable right now.',
}
