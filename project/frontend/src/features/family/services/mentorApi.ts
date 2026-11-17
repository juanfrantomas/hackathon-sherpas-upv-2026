import { BACKEND_API_URL, MENTOR_TIMEOUT_MS } from './config'

export interface MentorRequest {
  /** Case slug under `cases/`, e.g. `timothy-melanie-weah`. */
  caseId: string
  question: string
  /** `refranero`, `sencillo` or `formal`. The persona decides when it is empty. */
  style?: string | null
  /** Which member of the couple is speaking: `both`, `timothy`, `melanie`… */
  partner?: string | null
  /** The milestone the household opened, so the mentor can focus on it. */
  topic?: string | null
}

export interface MentorResponse {
  status: string
  case_id: string
  short_id: string
  /** Whether the mentor had to read the plan. */
  mcp_used: boolean
  voice: string
  style: string
  style_key: string
  partner_mode: string | null
  /** The sections the mentor read, for the "what did it look at" panel. */
  consulted: string[]
  answer: string
  /** The audio of the answer, relative to the backend. */
  audio_url: string | null
}

export class MentorApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(message: string, code = 'NETWORK_ERROR', status = 0) {
    super(message)
    this.name = 'MentorApiError'
    this.code = code
    this.status = status
  }
}

/**
 * Asks the AI mentor a question about a household's plan.
 *
 * The backend is the only component that holds the team AI key; the browser
 * never sees a credential.
 */
export async function askMentor({
  caseId,
  question,
  style,
  partner,
  topic,
}: MentorRequest): Promise<MentorResponse> {
  let response: Response
  try {
    response = await fetch(`${BACKEND_API_URL}/api/voice/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        case_id: caseId,
        question,
        style: style ?? null,
        partner: partner ?? null,
        topic: topic ?? null,
      }),
      signal: AbortSignal.timeout(MENTOR_TIMEOUT_MS),
    })
  } catch (cause) {
    throw new MentorApiError(
      `Could not reach the mentor: ${cause instanceof Error ? cause.message : 'network error'}`,
    )
  }

  if (!response.ok) {
    throw new MentorApiError(`The mentor replied with status ${response.status}`)
  }

  let payload: Partial<MentorResponse>
  try {
    payload = (await response.json()) as Partial<MentorResponse>
  } catch {
    throw new MentorApiError('The mentor sent a reply we could not read')
  }

  const answer = payload.answer?.trim()
  if (!answer) {
    throw new MentorApiError('The mentor sent an empty answer')
  }

  return payload as MentorResponse
}

/** The absolute address of an audio file the backend served. */
export function audioUrl(path: string | null | undefined): string | null {
  if (!path) return null
  if (/^https?:\/\//i.test(path)) return path
  return `${BACKEND_API_URL}${path.startsWith('/') ? '' : '/'}${path}`
}
