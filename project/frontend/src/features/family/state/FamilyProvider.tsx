import { useCallback, useMemo, useReducer, type Dispatch, type ReactNode } from 'react'
import type { FamilyScreen, Navigate, NavigationState } from '../types'
import { getFamily } from '../data/families'
import {
  createInitialFamilyFeatureState,
  familyReducer,
  type FamilyAction,
} from './familyReducer'
import { useApiMilestones } from './useApiMilestones'
import {
  completedMilestones,
  currentMilestone,
  milestonesWithStatus,
  pendingMilestones,
} from './selectors'
import {
  FamilyDataContext,
  NavigationContext,
  type FamilyDataValue,
  type NavigationValue,
} from './contexts'

/**
 * Owns every piece of family-app state and hands it out through two contexts:
 * one for the household and its demo state, one for where the user is.
 *
 * Splitting them keeps screen changes from re-rendering the whole app.
 */
export function FamilyProvider({ children }: { children: ReactNode }) {
  const [state, rawDispatch] = useReducer(
    familyReducer,
    undefined,
    createInitialFamilyFeatureState,
  )

  const family = useMemo(() => getFamily(state.familyId), [state.familyId])
  const familyState = state.states[state.familyId]

  const api = useApiMilestones(family.caseId)
  const live = api.milestones
  const { setStatus, reviewDone } = api

  // With a backend the milestone changes go to the API, which stays the source
  // of truth; everything else (navigation, voice, check-in log) stays local.
  const dispatch = useCallback<Dispatch<FamilyAction>>(
    (action) => {
      if (!live) return rawDispatch(action)
      switch (action.type) {
        case 'set_milestone_status':
          void setStatus(action.milestoneId, action.status)
          return
        case 'complete_milestone':
          void setStatus(action.milestoneId, 'completed')
          return
        case 'commit_checkin': {
          rawDispatch(action)
          const { milestoneId, answer, note } = action.payload
          if (milestoneId) {
            const status = live.find((m) => m.id === milestoneId)?.status
            void (async () => {
              if (answer === 'progress' && status === 'not_started') {
                await setStatus(milestoneId, 'in_progress')
              }
              await reviewDone(milestoneId, note || null)
            })()
          }
          return
        }
        default:
          return rawDispatch(action)
      }
    },
    [live, setStatus, reviewDone],
  )

  const milestones = useMemo(
    () => milestonesWithStatus(family, familyState, live),
    [family, familyState, live],
  )
  const completed = useMemo(() => completedMilestones(milestones), [milestones])
  const pending = useMemo(() => pendingMilestones(milestones), [milestones])
  const current = useMemo(() => currentMilestone(milestones), [milestones])

  const dataValue = useMemo<FamilyDataValue>(
    () => ({
      familyId: state.familyId,
      family,
      state: familyState,
      states: state.states,
      dispatch,
      milestones,
      completed,
      pending,
      current,
      milestonesStale: api.stale,
      milestonesError: api.error,
    }),
    [
      state.familyId,
      family,
      familyState,
      state.states,
      milestones,
      completed,
      pending,
      current,
      dispatch,
      api.stale,
      api.error,
    ],
  )

  const navigationValue = useMemo<NavigationValue>(
    () => ({
      screen: state.screen,
      nav: state.nav,
      screenKey: state.screenKey,
      go: ((screen: FamilyScreen, options) =>
        rawDispatch({ type: 'navigate', screen, options })) satisfies Navigate,
      setNav: (nav: Partial<NavigationState>) => rawDispatch({ type: 'set_nav', nav }),
    }),
    [state.screen, state.nav, state.screenKey],
  )

  return (
    <FamilyDataContext.Provider value={dataValue}>
      <NavigationContext.Provider value={navigationValue}>
        {children}
      </NavigationContext.Provider>
    </FamilyDataContext.Provider>
  )
}

