import { Button } from '../../../../components/ui/Button'
import { StatusIcon } from '../../../../components/ui/StatusIcon'
import { CHANGE_REASONS } from '../../data/changeReasons'
import type { Family } from '../../types'
import type { CheckInActions, CheckInState } from './types'

export interface CheckInOutcomeProps {
  /** Which of the three outcome steps is showing. */
  step: 'progress' | 'time' | 'change'
  family: Family
  state: CheckInState
  actions: CheckInActions
  /** Title of the milestone the check-in is about. */
  milestoneTitle: string | undefined
}

/**
 * The three steps that follow the first question: what the household achieved,
 * whether it needs more time, or what has changed.
 */
export function CheckInOutcome({
  step,
  family,
  state,
  actions,
  milestoneTitle,
}: CheckInOutcomeProps) {
  if (step === 'progress') {
    return (
      <>
        <h1 className="h-title">That's good to hear.</h1>
        <p className="muted">
          Is &quot;{milestoneTitle ?? ''}&quot; complete, or still in progress?
        </p>
        <div className="choice-list">
          <button
            className="choice"
            onClick={() => {
              actions.completeMilestone()
              actions.setStep('share')
            }}
          >
            <StatusIcon status="completed" size={22} />
            <span>It's complete</span>
          </button>
          <button className="choice" onClick={() => actions.setStep('share')}>
            <StatusIcon status="in_progress" size={22} />
            <span>Still working on it</span>
          </button>
        </div>
      </>
    )
  }

  if (step === 'time') {
    return (
      <>
        <h1 className="h-title">That's completely fine.</h1>
        <p className="muted">
          Plans move at the pace of real life. We'll check in again next month.
          Your mentor is here if anything feels unclear.
        </p>
        <Button
          block
          variant="secondary"
          icon="mic"
          onClick={() => actions.talkToMentor(family.nextStep.topic)}
        >
          Talk it through first
        </Button>
        <Button block onClick={() => actions.setStep('share')}>
          Continue
        </Button>
      </>
    )
  }

  return (
    <>
      <h1 className="h-title">Has anything important changed since your last review?</h1>
      <p className="muted">Choose what fits best.</p>

      <div className="chip-grid">
        {CHANGE_REASONS.map((option) => (
          <button
            key={option}
            className={`pill pill--lg${state.reason === option ? ' is-on' : ''}`}
            onClick={() => actions.setReason(option)}
          >
            {option}
          </button>
        ))}
      </div>

      <label className="field" htmlFor="ci-note">
        <span className="field__label">
          Anything you'd like to add? <span className="muted">Optional</span>
        </span>
        <textarea
          id="ci-note"
          rows={3}
          value={state.note}
          onChange={(event) => actions.setNote(event.target.value)}
          placeholder="A sentence is enough."
        />
      </label>

      <Button block disabled={!state.reason} onClick={() => actions.setStep('review')}>
        Continue
      </Button>
    </>
  )
}
