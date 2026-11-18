import { createContext, type Dispatch } from 'react'
import type {
  Family,
  FamilyId,
  FamilyScreen,
  FamilyState,
  Navigate,
  NavigationState,
  VoiceState,
} from '../types'
import type { FamilyAction } from './familyReducer'
import type { MilestoneWithStatus } from './selectors'

export interface FamilyDataValue {
  familyId: FamilyId
  /** The household currently being demoed. */
  family: Family
  /** Demo state of the current household. */
  state: FamilyState
  /** Demo state of every household. */
  states: Record<FamilyId, FamilyState>
  dispatch: Dispatch<FamilyAction>
  /** The household's milestones with their current status. */
  milestones: MilestoneWithStatus[]
  completed: MilestoneWithStatus[]
  pending: MilestoneWithStatus[]
  /** The milestone the household is working on, if any. */
  current: MilestoneWithStatus | undefined
  /** The backend answered from an older copy of the plan. */
  milestonesStale: boolean
  /** Why the backend could not be used or a change failed, if it happened. */
  milestonesError: string | null
}

export interface NavigationValue {
  screen: FamilyScreen
  nav: NavigationState
  voice: VoiceState
  /** Changes whenever the visible screen changes; used to replay animations. */
  screenKey: number
  go: Navigate
  setNav: (nav: Partial<NavigationState>) => void
  setVoice: (voice: VoiceState) => void
}

export const FamilyDataContext = createContext<FamilyDataValue | null>(null)
export const NavigationContext = createContext<NavigationValue | null>(null)
