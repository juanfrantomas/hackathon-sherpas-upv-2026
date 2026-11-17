import { Button } from '../../../../components/ui/Button'
import { Card } from '../../../../components/ui/Card'
import { Eyebrow } from '../../../../components/ui/Eyebrow'
import { Icon } from '../../../../components/ui/Icon'
import { Toggle } from '../../../../components/ui/Toggle'
import type { CheckInActions, CheckInState } from './types'

export interface CheckInSharingProps {
  /** Which of the three sharing steps is showing. */
  step: 'review' | 'share' | 'done'
  state: CheckInState
  actions: CheckInActions
  /** The summary that will be shared with the advisor. */
  summary: string
}

/** The last steps: asking for a review, choosing what to share, and the end. */
export function CheckInSharing({ step, state, actions, summary }: CheckInSharingProps) {
  if (step === 'review') {
    return (
      <>
        <div className="callout">
          <Icon name="info" size={20} />
          <div>
            <strong>A change like this may affect your plan.</strong>
            <p className="small">
              MySherpas doesn't recalculate your plan automatically. The right next
              step is a plan review, so your numbers reflect your new situation.
            </p>
          </div>
        </div>

        <div className="choice-list">
          <button
            className={`choice${state.review === 'request' ? ' is-on' : ''}`}
            onClick={() => {
              actions.setReview('request')
              actions.setShared(true)
              actions.setStep('share')
            }}
          >
            <Icon name="calendar" size={20} />
            <span>Request a plan review</span>
          </button>
          <button
            className={`choice${state.review === 'later' ? ' is-on' : ''}`}
            onClick={() => {
              actions.setReview('later')
              actions.setStep('share')
            }}
          >
            <Icon name="edit" size={20} />
            <span>Not now, just note it</span>
          </button>
        </div>
      </>
    )
  }

  if (step === 'share') {
    return (
      <>
        <h1 className="h-title">Share with your advisor?</h1>
        <p className="muted">
          Only what you see below is shared. Your conversations with the mentor stay
          private.
        </p>

        <Card className="share-preview">
          <Eyebrow>What your advisor will see</Eyebrow>
          <p>
            <strong>{summary}</strong>
          </p>
          {state.note && <p className="small">&quot;{state.note}&quot;</p>}
        </Card>

        <Toggle
          id="ci-share"
          checked={state.shared}
          onChange={actions.setShared}
          label="Share this update with my advisor"
        />

        {state.review === 'request' && !state.shared && (
          <p className="small warn-text">
            Your review request needs to be shared to reach your advisor.
          </p>
        )}

        <Button block onClick={actions.finish}>
          Finish check-in
        </Button>
      </>
    )
  }

  return (
    <div className="done">
      <div className="done__mark">
        <Icon name="check" size={28} stroke={2.2} />
      </div>
      <h1 className="h-title">Thanks for checking in.</h1>
      <p className="muted">
        {state.review === 'request' && state.shared
          ? 'Your advisor will see your review request. Until then, nothing in your plan changes.'
          : state.shared
            ? 'Your update was shared with your advisor.'
            : 'Your update is saved privately.'}
      </p>
      <Button block onClick={actions.seeMyProgress}>
        See my progress
      </Button>
      <Button block variant="ghost" onClick={actions.backToHome}>
        Back to home
      </Button>
    </div>
  )
}
