import { MILESTONES_API_URL, MILESTONES_TIMEOUT_MS } from './config'
import type {
  ApiErrorBody,
  Milestone,
  MilestoneListResponse,
  MilestoneStatus,
  NotificationListResponse,
  ProgressSummary,
  ReviewCompletedResponse,
  SyncState,
  TaskStatus,
} from './milestones.types'

export class MilestonesApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(message: string, code = 'NETWORK_ERROR', status = 0) {
    super(message)
    this.name = 'MilestonesApiError'
    this.code = code
    this.status = status
  }
}

async function request<T>(
  path: string,
  init: { method?: string; body?: unknown } = {},
): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${MILESTONES_API_URL}/api${path}`, {
      method: init.method ?? 'GET',
      headers: init.body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      signal: AbortSignal.timeout(MILESTONES_TIMEOUT_MS),
    })
  } catch (cause) {
    throw new MilestonesApiError(
      `Could not reach the milestones service: ${cause instanceof Error ? cause.message : 'network error'}`,
    )
  }

  if (!response.ok) {
    let body: Partial<ApiErrorBody> = {}
    try {
      body = (await response.json()) as Partial<ApiErrorBody>
    } catch {
      /* keep the generic message */
    }
    throw new MilestonesApiError(
      body.error?.message ?? `The milestones service replied with status ${response.status}`,
      body.error?.code ?? 'HTTP_ERROR',
      response.status,
    )
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new MilestonesApiError('The milestones service sent a reply we could not read')
  }
}

const base = (caseId: string) => `/cases/${encodeURIComponent(caseId)}`
const ms = (caseId: string, milestoneId: string) =>
  `${base(caseId)}/milestones/${encodeURIComponent(milestoneId)}`

export const listMilestones = (caseId: string) =>
  request<MilestoneListResponse>(`${base(caseId)}/milestones`)

export const setMilestoneStatus = (caseId: string, milestoneId: string, status: MilestoneStatus) =>
  request<Milestone>(`${ms(caseId, milestoneId)}/status`, { method: 'PATCH', body: { status } })

export const completeMilestone = (caseId: string, milestoneId: string) =>
  request<Milestone>(`${ms(caseId, milestoneId)}/complete`, {
    method: 'POST',
    body: { confirmed: true, note: null },
  })

export const setTaskStatus = (
  caseId: string,
  milestoneId: string,
  taskId: string,
  status: TaskStatus,
) =>
  request<unknown>(`${ms(caseId, milestoneId)}/tasks/${encodeURIComponent(taskId)}`, {
    method: 'PATCH',
    body: { status },
  })

export const completeReview = (caseId: string, milestoneId: string, note: string | null) =>
  request<ReviewCompletedResponse>(`${ms(caseId, milestoneId)}/checkins/complete`, {
    method: 'POST',
    body: { note },
  })

export const listNotifications = (caseId: string) =>
  request<NotificationListResponse>(`${base(caseId)}/notifications`)

export const getCaseProgress = (caseId: string) =>
  request<ProgressSummary>(`${base(caseId)}/progress`)

export const syncCase = (caseId: string) =>
  request<SyncState>(`${base(caseId)}/sync`, { method: 'POST', body: { force: false } })
