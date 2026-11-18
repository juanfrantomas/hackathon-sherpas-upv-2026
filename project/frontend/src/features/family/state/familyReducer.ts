import type {
  Family,
  FamilyId,
  FamilyScreen,
  FamilyState,
  MilestoneStatus,
  NavigationState,
  NavigateOptions,
} from '../types'
import { FAMILIES } from '../data/families'

export const DEFAULT_NAVIGATION: NavigationState = {
  planSection: 'summary',
  planCard: null,
  progressTab: 'milestones',
  openMilestone: null,
  mentorTopic: null,
  mentorFrom: null,
}

/** The answer a household gave to the first check-in question. */
export type CheckinAnswer = 'progress' | 'time' | 'change'

/** Whether the household asked for a plan review, or just noted the change. */
export type CheckinReviewChoice = 'request' | 'later' | null

export interface FamilyFeatureState {
  familyId: FamilyId
  states: Record<FamilyId, FamilyState>
  screen: FamilyScreen
  nav: NavigationState
  /** Bumped whenever the visible screen changes, to replay the enter animation. */
  screenKey: number
}

export type FamilyAction =
  | { type: 'select_family'; familyId: FamilyId }
  | { type: 'reset_all' }
  | { type: 'set_milestone_status'; milestoneId: string; status: MilestoneStatus }
  | { type: 'complete_milestone'; milestoneId: string }
  | { type: 'commit_checkin'; payload: CommitCheckinPayload }
  | { type: 'mark_watched' }
  | { type: 'navigate'; screen: FamilyScreen; options?: NavigateOptions }
  | { type: 'set_nav'; nav: Partial<NavigationState> }

export interface CommitCheckinPayload {
  summary: string
  shared: boolean
  note: string
  review: CheckinReviewChoice
  answer: CheckinAnswer
  milestoneId: string | null
}

/** Initial demo state for one household. */
export function createInitialFamilyState(family: Family): FamilyState {
  return {
    milestones: Object.fromEntries(
      family.milestones.map((milestone) => [milestone.id, milestone.status]),
    ),
    checkins: [],
    reviewRequested: false,
    sharedItems: family.advisor.shared,
    watched: false,
    nextCheckin: family.milestones.find((milestone) => milestone.checkin)?.checkin ?? 'Dec 14',
  }
}

/** Initial demo state for every household. */
export function createInitialFamilyStates(
  families: readonly Family[] = FAMILIES,
): Record<FamilyId, FamilyState> {
  return Object.fromEntries(
    families.map((family) => [family.id, createInitialFamilyState(family)]),
  ) as Record<FamilyId, FamilyState>
}

export function createInitialFamilyFeatureState(
  familyId: FamilyId = FAMILIES[0].id,
): FamilyFeatureState {
  return {
    familyId,
    states: createInitialFamilyStates(),
    screen: 'welcome',
    nav: { ...DEFAULT_NAVIGATION },
    screenKey: 0,
  }
}

/**
 * All family-app state transitions, as pure functions.
 *
 * The prototype kept this state in a dozen `useState` calls inside the root
 * component and threaded it down through props. A reducer makes the same
 * transitions explicit, and — importantly — makes the check-in wizard's
 * multi-field commit a single atomic update.
 */
export function familyReducer(
  state: FamilyFeatureState,
  action: FamilyAction,
): FamilyFeatureState {
  switch (action.type) {
    case 'select_family':
      return {
        ...state,
        familyId: action.familyId,
        screen: 'welcome',
        nav: { ...DEFAULT_NAVIGATION },
            screenKey: state.screenKey + 1,
      }

    case 'reset_all':
      return {
        ...state,
        states: createInitialFamilyStates(),
        screen: 'welcome',
        nav: { ...DEFAULT_NAVIGATION },
            screenKey: state.screenKey + 1,
      }

    case 'set_milestone_status':
      return withCurrentFamilyState(state, (current) => ({
        ...current,
        milestones: {
          ...current.milestones,
          [action.milestoneId]: action.status,
        },
      }))

    case 'complete_milestone':
      return withCurrentFamilyState(state, (current) => ({
        ...current,
        milestones: {
          ...current.milestones,
          [action.milestoneId]: 'completed',
        },
      }))

    case 'commit_checkin':
      return withCurrentFamilyState(state, (current) => {
        const { summary, shared, note, review, answer, milestoneId } = action.payload
        const promotesMilestone =
          answer === 'progress' &&
          milestoneId !== null &&
          current.milestones[milestoneId] === 'not_started'

        return {
          ...current,
          checkins: [
            ...current.checkins,
            { date: 'Today', summary, shared, note },
          ],
          reviewRequested: current.reviewRequested || review === 'request',
          sharedItems: shared
            ? [
                ...current.sharedItems,
                {
                  kind: review === 'request' ? 'review' : 'update',
                  text: summary + (note ? `. "${note}"` : ''),
                  date: 'Today',
                },
              ]
            : current.sharedItems,
          milestones: promotesMilestone
            ? { ...current.milestones, [milestoneId]: 'in_progress' }
            : current.milestones,
        }
      })

    case 'mark_watched':
      return withCurrentFamilyState(state, (current) => ({
        ...current,
        watched: true,
      }))

    case 'navigate': {
      const options = action.options ?? {}
      const nav: Partial<NavigationState> = {}

      if (options.section) {
        nav.planSection = options.section
        nav.planCard = options.card ?? null
      }
      if (options.tab) {
        nav.progressTab = options.tab
      }
      if (options.open !== undefined) {
        nav.openMilestone = options.open
      }
      if (action.screen === 'mentor') {
        nav.mentorTopic = options.topic ?? null
        nav.mentorFrom = options.from ?? (state.screen !== 'mentor' ? state.screen : 'home')
      }

      const screenChanged = action.screen !== state.screen
      return {
        ...state,
        nav: { ...state.nav, ...nav },
        screen: action.screen,
        screenKey: screenChanged ? state.screenKey + 1 : state.screenKey,
      }
    }

    case 'set_nav':
      return { ...state, nav: { ...state.nav, ...action.nav } }

    default:
      return state
  }
}

function withCurrentFamilyState(
  state: FamilyFeatureState,
  update: (current: FamilyState) => FamilyState,
): FamilyFeatureState {
  const current = state.states[state.familyId]
  return {
    ...state,
    states: {
      ...state.states,
      [state.familyId]: update(current),
    },
  }
}
