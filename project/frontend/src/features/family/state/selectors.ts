import type { Family, FamilyState, Milestone } from '../types'

/** A milestone paired with its current status in the demo state. */
export type MilestoneWithStatus = Milestone & { status: Milestone['status'] }

/** Pairs each plan milestone with the status held in the demo state. */
export function milestonesWithStatus(
  family: Family,
  state: FamilyState,
  live: Milestone[] | null = null,
): MilestoneWithStatus[] {
  // Backend milestones carry their own, authoritative status.
  if (live) return live
  return family.milestones.map((milestone) => ({
    ...milestone,
    status: state.milestones[milestone.id] ?? milestone.status,
  }))
}

/** The milestone the household is working on: in progress, else next up. */
export function currentMilestone(
  milestones: MilestoneWithStatus[],
): MilestoneWithStatus | undefined {
  return (
    milestones.find((milestone) => milestone.status === 'in_progress') ??
    milestones.find((milestone) => milestone.status !== 'completed')
  )
}

export function completedMilestones(
  milestones: MilestoneWithStatus[],
): MilestoneWithStatus[] {
  return milestones.filter((milestone) => milestone.status === 'completed')
}

export function pendingMilestones(
  milestones: MilestoneWithStatus[],
): MilestoneWithStatus[] {
  return milestones.filter((milestone) => milestone.status !== 'completed')
}
