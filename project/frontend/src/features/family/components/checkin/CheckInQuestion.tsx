import { Icon } from '../../../../components/ui/Icon'
import { Eyebrow } from '../../../../components/ui/Eyebrow'
import type { Family } from '../../types'
import type { CheckInActions } from './types'

export interface CheckInQuestionProps {
  family: Family
  actions: CheckInActions
}

/** Step 1 — how is the household getting on with its current priority? */
export function CheckInQuestion({ family, actions }: CheckInQuestionProps) {
  return (
    <>
      <div className="stack-2">
        <Eyebrow>Your current priority</Eyebrow>
        <h1 className="h-title">
          Have you made progress on {family.checkinPriority}?
        </h1>
        <p className="muted">
          There's no wrong answer. This helps MySherpas show you what's
          useful next.
        </p>
      </div>

      <div className="choice-list">
        <button
          className="choice"
          onClick={() => {
            actions.setAnswer('progress')
            actions.setStep('progress')
          }}
        >
          <Icon name="check" size={20} />
          <span>I've made progress.</span>
        </button>
        <button
          className="choice"
          onClick={() => {
            actions.setAnswer('time')
            actions.setStep('time')
          }}
        >
          <Icon name="calendar" size={20} />
          <span>I need more time.</span>
        </button>
        <button
          className="choice"
          onClick={() => {
            actions.setAnswer('change')
            actions.setStep('change')
          }}
        >
          <Icon name="flag" size={20} />
          <span>Something has changed.</span>
        </button>
        <button
          className="choice"
          onClick={() => actions.talkToMentor('Your check-in')}
        >
          <Icon name="mic" size={20} />
          <span>Talk to my AI mentor.</span>
        </button>
      </div>
    </>
  )
}
