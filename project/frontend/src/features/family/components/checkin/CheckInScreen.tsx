import { useState } from 'react'
import { ScreenHeader } from '../ScreenHeader'
import { CheckInOutcome } from './CheckInOutcome'
import { CheckInQuestion } from './CheckInQuestion'
import { CheckInSharing } from './CheckInSharing'
import type { CheckInActions, CheckInState } from './types'
import type { CheckinAnswer, CheckinReviewChoice } from '../../state/familyReducer'
import type { CheckinStep, Family, Navigate } from '../../types'

const STEP_NUMBER: Record<CheckinStep, number> = {
  q1: 1,
  progress: 2,
  time: 2,
  change: 2,
  review: 3,
  share: 3,
  done: 3,
}

const INITIAL_STATE: CheckInState = {
  step: 'q1',
  answer: null,
  reason: null,
  review: null,
  shared: false,
  note: '',
}

export interface CheckInScreenProps {
  family: Family
  /** The milestone the check-in refers to. */
  milestoneId: string | null
  milestoneTitle: string | undefined
  onCompleteMilestone: (milestoneId: string) => void
  onFinish: (payload: {
    summary: string
    shared: boolean
    note: string
    review: CheckinReviewChoice
    answer: CheckinAnswer
    milestoneId: string | null
  }) => void
  go: Navigate
}

/** Screen 7 — the two-minute monthly check-in. */
export function CheckInScreen({
  family,
  milestoneId,
  milestoneTitle,
  onCompleteMilestone,
  onFinish,
  go,
}: CheckInScreenProps) {
  const [state, setState] = useState<CheckInState>(INITIAL_STATE)

  const summary =
    state.answer === 'progress'
      ? `Made progress on "${milestoneTitle ?? ''}"`
      : state.answer === 'time'
        ? 'Needs more time on the current priority'
        : state.answer === 'change'
          ? `Reported a change: ${state.reason ?? ''}${
              state.review === 'request' ? ' · plan review requested' : ''
            }`
          : ''

  const actions: CheckInActions = {
    setStep: (step) => setState((current) => ({ ...current, step })),
    setAnswer: (answer) => setState((current) => ({ ...current, answer })),
    setReason: (reason) => setState((current) => ({ ...current, reason })),
    setReview: (review) => setState((current) => ({ ...current, review })),
    setShared: (shared) => setState((current) => ({ ...current, shared })),
    setNote: (note) => setState((current) => ({ ...current, note })),
    completeMilestone: () => {
      if (milestoneId) onCompleteMilestone(milestoneId)
    },
    finish: () => {
      onFinish({
        summary,
        shared: state.shared,
        note: state.note,
        review: state.review,
        answer: state.answer ?? 'time',
        milestoneId,
      })
      setState((current) => ({ ...current, step: 'done' }))
    },
    talkToMentor: (topic) => go('mentor', { from: 'checkin', topic }),
    seeMyProgress: () => go('progress', { tab: 'journey' }),
    backToHome: () => go('home'),
  }

  const stepNumber = STEP_NUMBER[state.step]

  return (
    <div className="screen screen--checkin">
      <ScreenHeader
        title="Monthly check-in"
        onBack={() => go('progress', { tab: 'journey' })}
        right={
          <span className="micro muted step-count">
            {state.step !== 'done' ? `${stepNumber} of 3` : ''}
          </span>
        }
      />

      <div className="checkin-progress">
        <span
          style={{
            width:
              (state.step === 'done' ? 100 : (stepNumber / 3) * 100 - 15) + '%',
          }}
        />
      </div>

      <div className="pad stack-5 checkin" key={state.step}>
        {state.step === 'q1' && (
          <CheckInQuestion family={family} actions={actions} />
        )}

        {(state.step === 'progress' ||
          state.step === 'time' ||
          state.step === 'change') && (
          <CheckInOutcome
            step={state.step}
            family={family}
            state={state}
            actions={actions}
            milestoneTitle={milestoneTitle}
          />
        )}

        {(state.step === 'review' ||
          state.step === 'share' ||
          state.step === 'done') && (
          <CheckInSharing
            step={state.step}
            state={state}
            actions={actions}
            summary={summary}
          />
        )}
      </div>
    </div>
  )
}
