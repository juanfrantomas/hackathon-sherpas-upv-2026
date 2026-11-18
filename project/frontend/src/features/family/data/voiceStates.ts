import type { VoiceState } from '../types'

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
