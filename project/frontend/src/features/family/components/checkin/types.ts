import type { ChangeReason } from '../../data/changeReasons'
import type { CheckinAnswer, CheckinReviewChoice } from '../../state/familyReducer'
import type { CheckinStep } from '../../types'

/** Everything the check-in wizard remembers while it is open. */
export interface CheckInState {
  step: CheckinStep
  /** The household's answer to the first question. */
  answer: CheckinAnswer | null
  /** What changed, when the answer was "something has changed". */
  reason: ChangeReason | null
  /** Whether the household asked for a plan review. */
  review: CheckinReviewChoice
  /** Whether the update will be shared with the advisor. */
  shared: boolean
  /** Free-text note the household may add. */
  note: string
}

export interface CheckInActions {
  setStep: (step: CheckinStep) => void
  setAnswer: (answer: CheckinAnswer) => void
  setReason: (reason: ChangeReason) => void
  setReview: (review: CheckinReviewChoice) => void
  setShared: (shared: boolean) => void
  setNote: (note: string) => void
  /** Marks the milestone complete and moves on. */
  completeMilestone: () => void
  /** Writes the check-in to the household's state. */
  finish: () => void
  /** Opens the mentor. */
  talkToMentor: (topic: string) => void
  /** Returns to the journey screen. */
  seeMyProgress: () => void
  /** Returns to the home dashboard. */
  backToHome: () => void
}
