import { useEffect, useRef } from 'react'
import { Button } from '../../../components/ui/Button'
import { DemoTag } from '../../../components/ui/DemoTag'
import { Icon } from '../../../components/ui/Icon'
import { VoiceOrb } from './VoiceOrb'
import { useMentorSession } from '../state/useMentorSession'
import { useRealtimeVoice } from '../hooks/useRealtimeVoice'
import { useTypewriter } from '../hooks/useTypewriter'
import { VOICE_STATE_TEXT } from '../data/voiceStates'
import type { Family, Navigate, NavigationState, VoiceState } from '../types'

interface TranscriptLine {
  who: 'you' | 'mentor'
  text: string
  live?: boolean
  cut?: boolean
}

export interface MentorScreenProps {
  family: Family
  nav: NavigationState
  voice: VoiceState
  go: Navigate
}

/** Screen 4 — the voice mentor. */
export function MentorScreen({ family, nav, voice, go }: MentorScreenProps) {
  const session = useMentorSession()
  const live = useRealtimeVoice(family.caseId)
  const topic = nav.mentorTopic || family.mentor.topic
  const question = session.question
  const answer = session.answer
  const firstPrompt = family.mentor.prompts[0]

  const typedQuestion = useTypewriter(question, voice === 'listening', 30)
  const typedAnswer = useTypewriter(answer, voice === 'speaking', 40)
  const typedInterrupt = useTypewriter(firstPrompt, voice === 'interrupted', 40)

  const words = answer.split(' ')
  const cutAnswer = words.slice(0, Math.ceil(words.length * 0.42)).join(' ')

  const transcriptRef = useRef<HTMLDivElement>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // The backend sends the audio of the answer; it plays when the mentor speaks.
  useEffect(() => {
    if (voice !== 'speaking' || !session.audio) return
    const element = audioRef.current
    if (!element) return
    element.src = session.audio
    void element.play().catch(() => undefined)
  }, [voice, session.audio])

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
    }
  }, [typedQuestion, typedAnswer, typedInterrupt, voice])

  const lines: TranscriptLine[] = []
  if (voice === 'listening') {
    lines.push({ who: 'you', text: typedQuestion, live: true })
  }
  if (['thinking', 'speaking', 'interrupted', 'muted'].includes(voice)) {
    lines.push({ who: 'you', text: question })
  }
  if (voice === 'speaking') {
    lines.push({ who: 'mentor', text: typedAnswer, live: true })
  }
  if (voice === 'muted') {
    lines.push({ who: 'mentor', text: answer })
  }
  if (voice === 'interrupted') {
    lines.push({ who: 'mentor', text: `${cutAnswer} —`, cut: true })
    lines.push({ who: 'you', text: typedInterrupt, live: true })
  }

  const advance = () => {
    session.advance()
  }

  const endSession = () => {
    session.end()
    go(nav.mentorFrom || 'home')
  }

  return (
    <div className={`screen screen--mentor is-${voice}`}>
      <header className="mentor-head">
        <button
          className="icon-btn"
          onClick={endSession}
          aria-label="Close mentor"
        >
          <Icon name="chevronDown" size={22} />
        </button>
        <div className="mentor-head__mid">
          <strong>Your mentor</strong>
          <span className="topic-chip">
            <Icon name="plan" size={12} /> {topic}
          </span>
        </div>
        <DemoTag>{session.live ? 'Live' : 'Sample'}</DemoTag>
      </header>

      <div className="mentor-stage">
        <VoiceOrb state={voice} />
        <p className="mentor-state" aria-live="polite">
          {VOICE_STATE_TEXT[voice]}
        </p>
        {voice === 'speaking' && (
          <span className="interrupt-hint">
            <Icon name="mic" size={13} /> You can interrupt
          </span>
        )}
        <button
          className={`live-voice-btn${live.state === 'ready' ? ' is-on' : ''}`}
          onClick={() => {
            if (live.state === 'idle') {
              void live.connect({ topic })
            } else {
              live.disconnect()
            }
          }}
          aria-pressed={live.state === 'ready'}
        >
          <Icon name="sparkle" size={14} />
          {live.state === 'idle'
            ? 'Talk to your mentor live'
            : live.state === 'connecting'
              ? 'Opening the live voice…'
              : live.state === 'ready'
                ? 'Live voice on · stop'
                : 'The live voice failed'}
        </button>
      </div>

      {voice === 'error' ? (
        <div className="pad stack-3 mentor-error">
          <div className="callout callout--err">
            <Icon name="wifiOff" size={20} />
            <div>
              <strong>We couldn't connect to your mentor.</strong>
              <p className="small">
                Check your connection and try again. Your plan is still available to
                read.
              </p>
            </div>
          </div>
          <div className="row-2">
            <Button onClick={() => session.retry()} icon="replay">
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
                  onClick={() => session.ask(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          ) : (
            lines.map((line, index) => (
              <p
                key={`${line.who}-${index}`}
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

      {session.audio && (
        <audio ref={audioRef} preload="none" aria-hidden="true" />
      )}

      {live.state !== 'idle' && (
        <div className="pad stack-2">
          <div className="callout">
            <Icon name="mic" size={18} />
            <div>
              <strong>
                {live.state === 'connecting'
                  ? 'Opening the live voice…'
                  : live.state === 'ready'
                    ? `Live voice · ${live.session?.voice ?? ''}`
                    : 'The live voice failed'}
              </strong>
              {live.transcript && <p className="small">{live.transcript}</p>}
              {live.error && <p className="small muted">{live.error}</p>}
            </div>
          </div>
        </div>
      )}

      <div className="mentor-controls">
        <button
          className={`ctl${voice === 'muted' ? ' is-on' : ''}`}
          onClick={() => session.setMuted(voice !== 'muted')}
          aria-pressed={voice === 'muted'}
          aria-label={voice === 'muted' ? 'Unmute' : 'Mute'}
        >
          <Icon name={voice === 'muted' ? 'micOff' : 'mic'} size={22} />
          <span>{voice === 'muted' ? 'Unmute' : 'Mute'}</span>
        </button>

        <button
          className={`mic-main mic-main--${voice}`}
          onClick={advance}
          disabled={voice === 'error'}
          aria-label={voice === 'speaking' ? 'Interrupt' : 'Talk'}
        >
          <Icon
            name={voice === 'muted' ? 'micOff' : 'mic'}
            size={30}
            stroke={1.8}
          />
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
