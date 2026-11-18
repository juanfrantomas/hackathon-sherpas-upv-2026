import { useCallback, useEffect, useState } from 'react'
import { BACKEND_LIVE_ENABLED } from '../services/config'
import {
  getCouple,
  getMentorInsights,
  getSimulator,
  getStory,
  simulateDecisions,
  type CoupleOverview,
  type MentorInsightsResponse,
  type SimulatorResponse,
  type StoryResponse,
} from '../services/pillarsApi'

export interface PillarsValue {
  simulator: SimulatorResponse | null
  insights: MentorInsightsResponse | null
  couple: CoupleOverview | null
  story: StoryResponse | null
  /** The decisions the household switched on. */
  activeIds: string[]
  loading: boolean
  error: string | null
  toggleDecision: (id: string) => void
  refresh: () => Promise<void>
}

/**
 * The four pillars of the plan: the decision laboratory, the proactive
 * mentor, the couple mode and the financial story.
 *
 * They are read from the backend, which writes the words from the plan.
 */
export function usePillars(caseId: string): PillarsValue {
  const [simulator, setSimulator] = useState<SimulatorResponse | null>(null)
  const [insights, setInsights] = useState<MentorInsightsResponse | null>(null)
  const [couple, setCouple] = useState<CoupleOverview | null>(null)
  const [story, setStory] = useState<StoryResponse | null>(null)
  const [activeIds, setActiveIds] = useState<string[]>([])
  const [loading, setLoading] = useState(BACKEND_LIVE_ENABLED)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!BACKEND_LIVE_ENABLED) return
    setLoading(true)
    try {
      const [sim, ins, cpl, sto] = await Promise.all([
        getSimulator(caseId),
        getMentorInsights(caseId),
        getCouple(caseId),
        getStory(caseId),
      ])
      setSimulator(sim)
      setInsights(ins)
      setCouple(cpl)
      setStory(sto)
      setError(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const toggleDecision = useCallback(
    (id: string) => {
      setActiveIds((current) => {
        const next = current.includes(id)
          ? current.filter((item) => item !== id)
          : [...current, id]
        void simulateDecisions(caseId, next)
          .then(setSimulator)
          .catch(() => undefined)
        return next
      })
    },
    [caseId],
  )

  return { simulator, insights, couple, story, activeIds, loading, error, toggleDecision, refresh }
}
