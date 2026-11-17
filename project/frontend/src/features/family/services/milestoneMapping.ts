import type { Milestone, PlanSectionId } from '../types'
import type { Milestone as ApiMilestone } from './milestones.types'

/**
 * `needs_review` is a prototype state the API never stores: a milestone needs
 * review when a check-in is due or it is overdue.
 */
export function displayStatus(m: ApiMilestone): Milestone['status'] {
  if (m.status === 'completed' || m.status === 'cancelled') return m.status
  return m.checkin_pending || m.overdue ? 'needs_review' : m.status
}

/** Adapts an API milestone to the shape the screens already consume. */
export function fromApi(m: ApiMilestone): Milestone {
  return {
    id: m.id,
    title: m.title,
    why: m.why,
    action: m.action,
    section: m.section as PlanSectionId,
    status: displayStatus(m),
    checkin: m.checkin ?? undefined,
    category: m.category,
    taskProgress: m.task_progress,
    checkinPending: m.checkin_pending,
    overdue: m.overdue,
  }
}
