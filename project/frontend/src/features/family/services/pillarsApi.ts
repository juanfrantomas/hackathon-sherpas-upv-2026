import { BACKEND_API_URL, PILLARS_TIMEOUT_MS } from './config'

/* ------------------------------------------------------------------ *
 * The decision laboratory
 * ------------------------------------------------------------------ */

export interface DecisionPowerUp {
  id: string
  icon: string
  title: string
  short_action: string
  effort: string
  lifts_a_cap: boolean
  lock_label: string
  individual_impact: string
  mentor_question: string
  score_before: number
  score_after: number
  score_impact: number
  active: boolean
}

export interface TimelineComparison {
  milestone: string
  icon: string
  without_changes: string
  with_decisions: string
  highlighted_change: string
}

export interface PactCard {
  card_id: string
  icon: string
  title: string
  subtitle_for: string
  peace_percentage: number
  return_percentage: number
  resulting_score: number
  verdict: string
  mentor_question: string
  recommended: boolean
}

export interface SimulatorResponse {
  case_id: string
  short_id: string
  household_name: string
  score_base: number
  simulated_score: number
  score_delta: number
  synergy_detected: boolean
  synergy_message: string
  combo_mentor_question: string
  annual_saving_dollars: number
  saving_label: string
  time_impact: string
  visual_summary: string
  confetti: boolean
  power_ups: DecisionPowerUp[]
  timeline_comparison: TimelineComparison[]
  pact_cards: PactCard[]
  generated: boolean
}

/* ------------------------------------------------------------------ *
 * The proactive mentor and the jargon pills
 * ------------------------------------------------------------------ */

export interface ProactiveInsight {
  badge: string
  greeting: string
  message: string
  cta_label: string
  voice_question: string
}

export interface JargonPill {
  term: string
  short_tag: string
  metaphor_title: string
  metaphor_explanation: string
  family_impact: string
  voice_question: string
}

export interface MentorInsightsResponse {
  case_id: string
  short_id: string
  style_key: string
  style_label: string
  proactive_nudge: ProactiveInsight
  jargon_pills: JargonPill[]
  generated: boolean
}

/* ------------------------------------------------------------------ *
 * The couple mode
 * ------------------------------------------------------------------ */

export interface CoupleMember {
  key: string
  name: string
  role: string
  age: number
  retirement_age: number | null
  risk_profile: string
  personal_focus: string
}

export interface KidsGoalItem {
  id: string
  icon: string
  friendly_title: string
  visual_meta: string
  progress_percentage: number
  children_explanation: string
}

export interface HighFiveItem {
  id: string
  case_id: string
  from_member: string
  to_member: string
  milestone_title: string
  message: string
  created_at: string
}

export interface CoupleOverview {
  case_id: string
  is_couple: boolean
  members: CoupleMember[]
  consensus_bridge: string
  kids_safe_view: KidsGoalItem[]
  high_fives: HighFiveItem[]
  generated: boolean
}

/* ------------------------------------------------------------------ *
 * The financial story
 * ------------------------------------------------------------------ */

export interface StoryScene {
  scene_id: number
  chapter: string
  headline_figure: string
  title: string
  subtitle: string
  caption_narration: string
}

export interface StoryResponse {
  case_id: string
  short_id: string
  household_title: string
  city: string
  state: string
  is_couple: boolean
  score: number
  band: string
  voice_name: string
  style_key: string
  style_label: string
  main_challenge: string
  scenes: StoryScene[]
  full_narration_script: string
  first_step_cta: Record<string, unknown>
  generated: boolean
}

/* ------------------------------------------------------------------ *
 * The catalogue of households
 * ------------------------------------------------------------------ */

export interface CaseSummary {
  case_id: string
  short_id: string
  household_name: string
  city: string | null
  state: string | null
  is_couple: boolean
  members: string[]
  score: number | null
  band: string | null
  voice_style: string
  voice_label: string
  voice_name: string
  gemini_voice: string
  openai_voice: string
}

/* ------------------------------------------------------------------ *
 * The client
 * ------------------------------------------------------------------ */

export class PillarsApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(message: string, code = 'NETWORK_ERROR', status = 0) {
    super(message)
    this.name = 'PillarsApiError'
    this.code = code
    this.status = status
  }
}

async function request<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BACKEND_API_URL}/api${path}`, {
      method: init.method ?? 'GET',
      headers: init.body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      signal: AbortSignal.timeout(PILLARS_TIMEOUT_MS),
    })
  } catch (cause) {
    throw new PillarsApiError(
      `Could not reach the backend: ${cause instanceof Error ? cause.message : 'network error'}`,
    )
  }

  if (!response.ok) {
    throw new PillarsApiError(`The backend replied with status ${response.status}`)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new PillarsApiError('The backend sent a reply we could not read')
  }
}

const base = (caseId: string) => `/cases/${encodeURIComponent(caseId)}`

export const listCases = () => request<CaseSummary[]>('/cases')

export const getSimulator = (caseId: string) =>
  request<SimulatorResponse>(`${base(caseId)}/simulator`)

export const simulateDecisions = (caseId: string, activeIds: string[]) =>
  request<SimulatorResponse>(`${base(caseId)}/simulator`, {
    method: 'POST',
    body: { active_ids: activeIds },
  })

export const getMentorInsights = (caseId: string) =>
  request<MentorInsightsResponse>(`${base(caseId)}/mentor/insights`)

export const getCouple = (caseId: string) => request<CoupleOverview>(`${base(caseId)}/couple`)

export const sendHighFive = (
  caseId: string,
  body: { from_member: string; to_member: string; milestone_title: string; message: string },
) => request<HighFiveItem>(`${base(caseId)}/couple/high-five`, { method: 'POST', body })

export const getStory = (caseId: string) => request<StoryResponse>(`${base(caseId)}/story`)
