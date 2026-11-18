import { useCallback, useEffect, useRef, useState } from 'react'
import { MILESTONES_LIVE_ENABLED } from '../services/config'
import { fromApi } from '../services/milestoneMapping'
import {
  completeMilestone,
  completeReview,
  listMilestones,
  setMilestoneStatus,
} from '../services/milestonesApi'
import type { Milestone, MilestoneStatus } from '../types'

export interface ApiMilestonesValue {
  /** `null` until the backend answered; stays `null` when it is unreachable. */
  milestones: Milestone[] | null
  loading: boolean
  /** The data may be older than the plan, or came from the offline copy. */
  stale: boolean
  error: string | null
  setStatus: (milestoneId: string, status: MilestoneStatus) => Promise<void>
  reviewDone: (milestoneId: string, note: string | null) => Promise<void>
  refresh: () => Promise<void>
}

/** Loads the milestones of a case from the backend and applies changes to them. */
export function useApiMilestones(caseId: string): ApiMilestonesValue {
  const [milestones, setMilestones] = useState<Milestone[] | null>(null)
  const [loading, setLoading] = useState(MILESTONES_LIVE_ENABLED)
  const [stale, setStale] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const latest = useRef(0)

  const refresh = useCallback(async () => {
    if (!MILESTONES_LIVE_ENABLED) return
    const id = ++latest.current
    setLoading(true)
    try {
      const res = await listMilestones(caseId)
      if (id !== latest.current) return
      setMilestones(res.milestones.map(fromApi))
      setStale(res.meta?.stale ?? false)
      setError(null)
    } catch (cause) {
      if (id !== latest.current) return
      setMilestones(null)
      setError(cause instanceof Error ? cause.message : 'Unknown error')
    } finally {
      if (id === latest.current) setLoading(false)
    }
  }, [caseId])

  // A new household must never show the previous one's milestones.
  const [trackedCase, setTrackedCase] = useState(caseId)
  if (trackedCase !== caseId) {
    setTrackedCase(caseId)
    setMilestones(null)
  }

  useEffect(() => {
    void refresh()
  }, [refresh])

  /** Runs a mutation, then re-reads the list: the API is the source of truth. */
  const mutate = useCallback(
    async (run: () => Promise<unknown>) => {
      try {
        await run()
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'Unknown error')
      }
      await refresh()
    },
    [refresh],
  )

  const setStatus = useCallback(
    (milestoneId: string, status: MilestoneStatus) =>
      mutate(() => {
        if (status === 'completed') return completeMilestone(caseId, milestoneId)
        // `needs_review` is derived by the client; the API cannot store it.
        if (status === 'needs_review') return Promise.resolve()
        return setMilestoneStatus(caseId, milestoneId, status)
      }),
    [caseId, mutate],
  )

  const reviewDone = useCallback(
    (milestoneId: string, note: string | null) =>
      mutate(() => completeReview(caseId, milestoneId, note)),
    [caseId, mutate],
  )

  return { milestones, loading, stale, error, setStatus, reviewDone, refresh }
}
