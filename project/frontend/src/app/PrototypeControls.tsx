import { Icon } from '../components/ui/Icon'
import { VOICE_STATES } from '../features/family/data/voiceStates'
import { useMentorSession } from '../features/family/state/useMentorSession'
import type { Family, FamilyScreen, VoiceState } from '../features/family/types'

export interface PrototypeControlsProps {
  family: Family
  screen: FamilyScreen
  voice: VoiceState
  setVoice: (voice: VoiceState) => void
  /** Runs the sample conversation. */
  onPlaySample: () => void
  /** Restores every household's demo state. */
  onReset: () => void
}

/** The right-hand panel: the household, the voice states and the reset. */
export function PrototypeControls({
  family,
  screen,
  voice,
  setVoice,
  onPlaySample,
  onReset,
}: PrototypeControlsProps) {
  const mentor = useMentorSession()

  return (
    <aside className="controls">
      <h2 className="micro flow__h">Prototype controls</h2>

      <div className="ctl-block">
        <strong className="small">
          {family.names} {family.surname}
        </strong>
        <p className="micro muted">
          {family.challenge}. Facts from the hackathon case only.
        </p>
      </div>

      {screen === 'mentor' ? (
        <div className="ctl-block">
          <span className="small">
            <strong>Voice state</strong>
          </span>
          <div className="state-grid">
            {VOICE_STATES.map((option) => (
              <button
                key={option.id}
                className={`pill${voice === option.id ? ' is-on' : ''}`}
                onClick={() => setVoice(option.id)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <button
            className="btn btn--secondary btn--sm btn--block"
            onClick={onPlaySample}
          >
            <Icon name="play" size={16} />
            <span>Play sample conversation</span>
          </button>
          <p className="micro muted">
            {mentor.liveEnabled
              ? 'The mentor answers live from your plan. The dialogue is sample content written from the case facts.'
              : 'Voice is simulated. The dialogue is sample content written from the case facts, not a live AI response.'}
          </p>
        </div>
      ) : (
        <div className="ctl-block">
          <button
            className="btn btn--secondary btn--sm btn--block"
            onClick={onPlaySample}
          >
            <Icon name="mic" size={16} />
            <span>Demo: "{family.mentor.question}"</span>
          </button>
        </div>
      )}

      <div className="ctl-block">
        <button className="btn btn--ghost btn--sm btn--block" onClick={onReset}>
          <Icon name="replay" size={16} />
          <span>Reset demo</span>
        </button>
      </div>
    </aside>
  )
}
