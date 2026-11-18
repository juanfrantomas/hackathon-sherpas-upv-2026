/**
 * Types for the Financial Milestones API.
 *
 * Copy this file into the frontend, for example:
 *
 *   src/features/family/services/milestones.types.ts
 *
 * They mirror the Pydantic schemas of the backend one to one.  The machine
 * readable contract is `project/backend/openapi.json`; the guide that explains
 * the behaviour is `project/backend/docs/api-contract.md`.
 *
 * Money is sent as a JSON number and received as a decimal **string**, so no
 * precision is lost on the way.  Parse it with `Number(...)` only when you
 * need to do arithmetic, and keep the string for display.
 */

/* ------------------------------------------------------------------ *
 * Enumerations
 * ------------------------------------------------------------------ */

/** The lifecycle of a milestone.  Only the client changes it. */
export type MilestoneStatus =
  | 'not_started'
  | 'in_progress'
  | 'completed'
  | 'on_hold'
  | 'cancelled'

/** Educational milestones are about understanding, financial ones about results. */
export type MilestoneType = 'educational' | 'financial'

/** How urgent the household should treat the milestone. */
export type Priority = 'high' | 'medium' | 'low'

/** The closed catalogue of milestone categories. */
export type Category =
  | 'Debt'
  | 'Savings'
  | 'Investments'
  | 'Retirement'
  | 'Insurance & Protection'
  | 'Education'
  | 'Tax Planning'
  | 'Housing'
  | 'Estate Planning'
  | 'Financial Planning'
  | 'Other'

/** The six sections of a Sherpas plan. */
export type PlanSection =
  | 'summary'
  | 'retirement'
  | 'assets'
  | 'debt'
  | 'savings'
  | 'protection'

/** Where a financial figure comes from.  Both are kept side by side. */
export type ObservationSource = 'mcp' | 'client'

/** The kind of number an observation holds. */
export type MetricType =
  | 'balance'
  | 'coverage'
  | 'savings'
  | 'contribution'
  | 'ratio'
  | 'gap'

/** Whether the goal is to grow or to shrink. */
export type FinancialDirection = 'increase' | 'decrease'

/**
 * The state of the financial progress.
 *
 * `conflicting` means the plan and the household disagree; there is no
 * percentage in that case, and the UI must not invent one.
 */
export type FinancialProgressState =
  | 'not_quantifiable'
  | 'on_track'
  | 'achieved'
  | 'regressed'
  | 'conflicting'

/** The status of a task.  Tasks have no complex lifecycle. */
export type TaskStatus = 'pending' | 'completed'

/** Who proposed the task.  Tasks created by the household are never replaced. */
export type TaskOrigin = 'ai' | 'client'

/** The state of a scheduled review. */
export type CheckinStatus = 'scheduled' | 'completed' | 'missed'

/** The kind of internal notice. */
export type NotificationType = 'checkin_pending' | 'overdue'

/** The state of the synchronisation with the financial plan. */
export type SyncStatus = 'idle' | 'running' | 'success' | 'error'

/* ------------------------------------------------------------------ *
 * Milestones
 * ------------------------------------------------------------------ */

/** A pointer back to the plan data a recommendation comes from. */
export interface SourceRef {
  part: 'financial-health' | 'investment-analysis' | 'persona'
  section: string | null
  json_path: string | null
  quote: string | null
}

/** A concrete step the household has to take. */
export interface Task {
  id: string
  title: string
  description: string | null
  /** Position in the list, starting at 0. */
  order: number
  /** Only required tasks count towards the progress. */
  is_required: boolean
  status: TaskStatus
  origin: TaskOrigin
  completed_at: string | null
}

/**
 * A personalised step derived from the household's financial plan.
 *
 * The first seven fields are the contract the prototype already used.  They
 * keep their names and their meaning.
 */
export interface Milestone {
  /* --- legacy contract: do not rename --- */
  id: string
  title: string
  why: string
  action: string
  section: PlanSection
  status: MilestoneStatus
  /** Display format, for example "Dec 14".  Use `checkin_date` for logic. */
  checkin: string | null

  /* --- everything else --- */
  case_id: string
  category: Category
  type: MilestoneType
  priority: Priority
  tasks: Task[]
  /** Share of the required tasks that are done.  `null` = not applicable. */
  task_progress: number | null
  /** Share of the financial goal that is reached.  `null` = unknown. */
  financial_progress: number | null
  financial_progress_state: FinancialProgressState
  financial_metric_key: string | null
  financial_direction: FinancialDirection | null
  financial_start_value: string | null
  financial_target_value: string | null
  financial_unit: string | null
  financial_currency: string | null
  /** Target date of the milestone, `YYYY-MM-DD`.  Independent of `checkin`. */
  due_date: string | null
  /** A review was scheduled and the date has passed. */
  checkin_pending: boolean
  /** The next review, `YYYY-MM-DD`. */
  checkin_date: string | null
  /** The target date has passed and the milestone is still open. */
  overdue: boolean
  source: SourceRef[]
  created_at: string
  updated_at: string
  completed_at: string | null
  last_reviewed_at: string | null
}

/**
 * The fields the prototype already used.  A test can assert that a milestone
 * still carries all of them.
 */
export const LEGACY_MILESTONE_FIELDS = [
  'id',
  'title',
  'why',
  'action',
  'section',
  'status',
  'checkin',
] as const

/* ------------------------------------------------------------------ *
 * Listings
 * ------------------------------------------------------------------ */

/** Context about the listing itself. */
export interface MilestoneListMeta {
  case_id: string
  count: number
  /** The data may be older than the plan.  Show a notice when it is true. */
  stale: boolean
  /** Why the data may be outdated, for example "MCP_UNAVAILABLE". */
  stale_reason: string | null
  /** "mcp" or "local": where the plan was read from. */
  data_source: string | null
  last_successful_sync_at: string | null
}

/** The listing of the milestones of a case. */
export interface MilestoneListResponse {
  milestones: Milestone[]
  meta: MilestoneListMeta | null
  /** Present when the listing was requested with `?group_by=category`. */
  grouped_by_category: Record<Category, Milestone[]> | null
}

/** The aggregated progress of a case. */
export interface ProgressSummary {
  milestones_total: number
  completed: number
  in_progress: number
  not_started: number
  on_hold: number
  cancelled: number
  overdue: number
  checkins_pending: number
  task_progress_average: number | null
  financial_progress_average: number | null
}

/* ------------------------------------------------------------------ *
 * Tasks
 * ------------------------------------------------------------------ */

/** The operational progress of one milestone. */
export interface TaskProgress {
  milestone_id: string
  task_progress: number | null
  required_tasks: number
  completed_required_tasks: number
  optional_tasks: number
  completed_optional_tasks: number
  /** True when completing the tasks is enough to close the milestone. */
  auto_completable: boolean
}

/** The body of a task creation. */
export interface TaskCreateRequest {
  title: string
  description?: string | null
  is_required?: boolean
  order?: number
}

/** The body of a task change.  `status` completes or uncompletes it. */
export interface TaskUpdateRequest {
  status?: TaskStatus
  title?: string
  description?: string | null
  is_required?: boolean
}

/* ------------------------------------------------------------------ *
 * Financial observations
 * ------------------------------------------------------------------ */

/** A measured financial value. */
export interface Observation {
  id: string
  milestone_id: string
  metric_key: string
  metric_type: MetricType | string
  /** Decimal, as a string: "18000.00". */
  value: string
  unit: string
  currency: string | null
  observed_at: string
  source: ObservationSource
  is_conflicted: boolean
  note: string | null
  recorded_at: string
}

/** The body of an observation: a value the household declares. */
export interface ObservationCreateRequest {
  metric_key: string
  metric_type: MetricType | string
  /** A number or a decimal string.  It cannot be negative. */
  value: number | string
  unit: string
  currency?: string | null
  observed_at?: string | null
  note?: string | null
}

/** The description of a disagreement between the plan and the household. */
export interface ObservationConflict {
  metric_key: string
  mcp_value: string
  mcp_observed_at: string
  client_value: string
  client_observed_at: string
  difference: string
  resolution: string
}

export interface ObservationListResponse {
  observations: Observation[]
  conflict: ObservationConflict | null
}

/** The financial progress of a milestone and where its figures come from. */
export interface FinancialProgress {
  milestone_id: string
  /** `null` whenever a percentage would be an invention. */
  progress: number | null
  state: FinancialProgressState
  direction: FinancialDirection | null
  start_value: string | null
  target_value: string | null
  /** The source the calculation used, `null` when the sources disagree. */
  used_source: ObservationSource | null
  sources: Observation[]
  conflict: ObservationConflict | null
  metric_key: string | null
  unit: string | null
  currency: string | null
}

/* ------------------------------------------------------------------ *
 * Check-ins
 * ------------------------------------------------------------------ */

/** One scheduled review. */
export interface Checkin {
  id: string
  milestone_id: string
  title: string | null
  /** The date the review was planned for. */
  scheduled_date: string
  /** The date the review actually happened. */
  effective_date: string | null
  status: CheckinStatus
  completed_at: string | null
  /** The planned date has passed and the review did not happen. */
  pending: boolean
  note: string | null
}

export interface CheckinListResponse {
  checkins: Checkin[]
}

/** The review schedule of one milestone. */
export interface MilestoneCheckins {
  milestone_id: string
  next_review: string | null
  next_review_display: string | null
  pending: boolean
  overdue: boolean
  last_reviewed_at: string | null
  history: Checkin[]
}

/** The body of a review: the household reports that it happened. */
export interface ReviewCompletedRequest {
  effective_date?: string | null
  note?: string | null
}

export interface ReviewCompletedResponse {
  checkin: Checkin
  next_review: string | null
  next_review_display: string | null
  pending: boolean
}

/* ------------------------------------------------------------------ *
 * Notifications
 * ------------------------------------------------------------------ */

/** An internal notice about a pending review or an overdue milestone. */
export interface Notification {
  id: string
  case_id: string
  milestone_id: string | null
  type: NotificationType
  title: string
  body: string
  reference_date: string | null
  created_at: string
  read_at: string | null
}

export interface NotificationListResponse {
  notifications: Notification[]
  unread_count: number
}

export interface MarkReadResponse {
  read: number
}

/* ------------------------------------------------------------------ *
 * Synchronisation
 * ------------------------------------------------------------------ */

/** The body of a manual synchronisation. */
export interface SyncRequest {
  /** Ignore the fingerprint of the plan and the minimum interval. */
  force?: boolean
}

/** The state of the last synchronisation with the plan. */
export interface SyncState {
  case_id: string
  status: SyncStatus
  trigger: 'first_access' | 'interval' | 'manual' | null
  plan_fingerprint: string | null
  last_attempt_at: string | null
  last_success_at: string | null
  last_error_code: string | null
  last_error_message: string | null
  milestones_created: number
  milestones_updated: number
  milestones_kept: number
  ai_model: string | null
}

/* ------------------------------------------------------------------ *
 * Catalogues and errors
 * ------------------------------------------------------------------ */

/** One entry of the category catalogue. */
export interface CategoryInfo {
  id: string
  label: Category
  default_section: PlanSection
}

export interface CategoryCatalogue {
  categories: CategoryInfo[]
}

export interface SectionInfo {
  id: PlanSection
  label: string
}

export interface SectionCatalogue {
  sections: SectionInfo[]
}

/** The body of every error the API answers with. */
export interface ApiErrorBody {
  error: {
    code: ApiErrorCode
    message: string
    details: Record<string, unknown>
  }
}

/** Every error code the API can answer with. */
export type ApiErrorCode =
  | 'MCP_UNAVAILABLE'
  | 'MCP_AUTH_ERROR'
  | 'INVALID_CASE_ID'
  | 'CASE_NOT_ALLOWED'
  | 'FINANCIAL_PLAN_NOT_FOUND'
  | 'AI_PROVIDER_UNAVAILABLE'
  | 'AI_INVALID_RESPONSE'
  | 'AI_RESPONSE_TOO_LARGE'
  | 'DATABASE_ERROR'
  | 'MILESTONE_NOT_FOUND'
  | 'TASK_NOT_FOUND'
  | 'INVALID_STATUS_TRANSITION'
  | 'INVALID_FINANCIAL_OBSERVATION'
  | 'SYNC_CONFLICT'
  | 'GENERATION_DISABLED'
  | 'NOT_FOUND'
  | 'VALIDATION_ERROR'
  | 'HTTP_ERROR'
  | 'INTERNAL_ERROR'
