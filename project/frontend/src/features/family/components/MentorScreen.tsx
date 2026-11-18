import { useEffect, useRef } from 'react'
import { Button } from '../../../components/ui/Button'
import { Icon } from '../../../components/ui/Icon'
import { VoiceOrb } from './VoiceOrb'
import { useMentorSession } from '../state/useMentorSession'
import { VOICE_STATE_TEXT } from '../data/voiceStates'
import type { Family, Navigate, NavigationState } from '../types'

export interface MentorScreenProps {
  family: Family
  nav: NavigationState
  go: Navigate
}

/** Screen 4 — the live voice mentor, served by the backend's WebSocket. */
export function MentorScreen({ family, nav, go }: MentorScreenProps) {
  const mentor = useMentorSession()
  const { voice, lines, active, error, consulted } = mentor
  const topic = nav.mentorTopic || family.mentor.topic

  const transcriptRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
    }
  }, [lines])

  // Leaving the screen ends the live session (it costs credit while it is open).
  const { disconnect } = mentor
  useEffect(() => disconnect, [disconnect])

  const endSession = () => {
    mentor.disconnect()
    go(nav.mentorFrom || 'home')
  }

  const stateText =
    voice === 'error' && error ? error : VOICE_STATE_TEXT[voice]

  return (
    <div className={`screen screen--mentor is-${voice}`}>
      <header className="mentor-head">
        <button className="icon-btn" onClick={endSession} aria-label="Close mentor">
          <Icon name="chevronDown" size={22} />
        </button>
        <div className="mentor-head__mid">
          <strong>Your mentor</strong>
          <span className="topic-chip">
            <Icon name="plan" size={12} /> {topic}
          </span>
        </div>
        <span className="icon-btn-sp" />
      </header>

      <div className="mentor-stage">
        <VoiceOrb state={voice} />
        <p className="mentor-state" aria-live="polite">
          {stateText}
        </p>
        {voice === 'speaking' && (
          <span className="interrupt-hint">
            <Icon name="mic" size={13} /> You can interrupt
          </span>
        )}
        {consulted && (
          <span className="interrupt-hint">
            <Icon name="plan" size={13} /> Reading {consulted}
          </span>
        )}
      </div>

      {voice === 'error' ? (
        <div className="pad stack-3 mentor-error">
          <div className="callout callout--err">
            <Icon name="wifiOff" size={20} />
            <div>
              <strong>We couldn't connect to your mentor.</strong>
              <p className="small">
                {error ?? 'Check your connection and try again.'} Your plan is still
                available to read.
              </p>
            </div>
          </div>
          <div className="row-2">
            <Button onClick={mentor.start} icon="replay">
              Try again
            </Button>
            <Button variant="secondary" onClick={() => go('plan')}>
              Read my plan
            </Button>
          </div>
        </div>
      ) : (
        <div className="transcript" ref={transcriptRef} aria-label="Live transcript">
          {lines.length === 0 ? (
            <div className="prompts">
              <span className="micro muted">Try asking</span>
              {[family.mentor.question, ...family.mentor.prompts].map((prompt) => (
                <button
                  key={prompt}
                  className="prompt"
                  onClick={() => mentor.ask(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          ) : (
            lines.map((line) => (
              <p
                key={line.id}
                className={`line line--${line.who}${line.cut ? ' is-cut' : ''}`}
              >
                <span className="line__who">
                  {line.who === 'you' ? family.names.split(' ')[0] : 'Mentor'}
                </span>
                {line.text}
                {line.live && <span className="caret" />}
                {line.cut && <span className="cut-tag">Interrupted</span>}
              </p>
            ))
          )}
        </div>
      )}

      <div className="mentor-controls">
        <button
          className={`ctl${voice === 'muted' ? ' is-on' : ''}`}
          onClick={() => mentor.setMuted(!mentor.muted)}
          disabled={!active}
          aria-pressed={mentor.muted}
          aria-label={mentor.muted ? 'Unmute' : 'Mute'}
        >
          <Icon name={mentor.muted ? 'micOff' : 'mic'} size={22} />
          <span>{mentor.muted ? 'Unmute' : 'Mute'}</span>
        </button>

        <button
          className={`mic-main mic-main--${voice}`}
          onClick={mentor.start}
          disabled={active}
          aria-label={active ? 'Listening' : 'Talk to your mentor'}
        >
          <Icon name={mentor.muted ? 'micOff' : 'mic'} size={30} stroke={1.8} />
        </button>

        <button className="ctl ctl--end" onClick={endSession} aria-label="End session">
          <Icon name="phoneEnd" size={22} />
          <span>End</span>
        </button>
      </div>

      <p className="mentor-privacy">
        <Icon name="lock" size={12} />
        {' Private conversation. Educational guidance based on your plan, not a new plan.'}
      </p>
    </div>
  )
}
