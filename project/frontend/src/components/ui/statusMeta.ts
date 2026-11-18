import type { MilestoneStatus, Tone } from '../../features/family/types'

export interface StatusMeta {
  label: string
  tone: Tone
}

/** Label and colour tone for each milestone status. */
export const STATUS_META = {
  not_started: { label: 'Not started', tone: 'neutral' },
  in_progress: { label: 'In progress', tone: 'blue' },
  completed: { label: 'Completed', tone: 'ok' },
  needs_review: { label: 'Needs review', tone: 'warn' },
  on_hold: { label: 'On hold', tone: 'neutral' },
  cancelled: { label: 'Cancelled', tone: 'neutral' },
} as const satisfies Record<MilestoneStatus, StatusMeta>

export const MILESTONE_STATUSES = [
  'not_started',
  'in_progress',
  'completed',
  'needs_review',
] as const satisfies readonly MilestoneStatus[]
