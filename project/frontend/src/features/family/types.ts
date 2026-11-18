/**
 * Domain types for the MySherpas family app.
 *
 * The prototype was a minified React bundle, so these types are a faithful
 * reconstruction of the shapes the original code used — not recovered source.
 */

/** Lifecycle of a plan milestone. */
export type MilestoneStatus =
  | 'not_started'
  | 'in_progress'
  | 'completed'
  | 'needs_review'
  | 'on_hold'
  | 'cancelled'

/** Sections of a Sherpas financial plan. */
export type PlanSectionId =
  | 'summary'
  | 'retirement'
  | 'assets'
  | 'debt'
  | 'savings'
  | 'protection'

/** Screens of the family app. */
export type FamilyScreen =
  | 'welcome'
  | 'story'
  | 'home'
  | 'plan'
  | 'progress'
  | 'checkin'
  | 'mentor'

/** Voice states of the AI mentor. */
export type VoiceState =
  | 'ready'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'interrupted'
  | 'muted'
  | 'error'

/** Semantic colour tone used by chips and pills. */
export type Tone = 'neutral' | 'blue' | 'ok' | 'warn'

/** Tone of a home-screen focus tile. */
export type FocusTone = 'neutral' | 'ok' | 'warn'

/** Charts that can accompany a plan recommendation. */
export type ChartKind =
  | 'score'
  | 'cashDebt'
  | 'timelineCarter'
  | 'timelineLewis'
  | 'twoGoals'

/** Tabs of the progress screen. */
export type ProgressTab = 'milestones' | 'journey'

/** Steps of the monthly check-in wizard. */
export type CheckinStep =
  | 'q1'
  | 'progress'
  | 'time'
  | 'change'
  | 'review'
  | 'share'
  | 'done'

/** Top-level areas of the prototype shell. */
export type PrototypeMode = 'family' | 'system'

/** Identifiers of the four demo households. */
export type FamilyId = 'weah' | 'carter' | 'johnson' | 'lewis'

export interface HouseholdFact {
  label: string
  value: string
  sub?: string
}

export interface FocusArea {
  label: string
  detail: string
  tone: FocusTone
}

export interface NextStep {
  title: string
  why: string
  section: PlanSectionId
  milestone: string
  topic: string
}

export interface StoryChapter {
  chapter: string
  big: string
  label: string
  caption: string
}

export interface PlanCard {
  id: string
  title: string
  what: string
  why: string
  next: string
  chart?: ChartKind | null
  milestone?: string
}

/** A plan section is either populated with cards or explicitly pending. */
export interface PlanSection {
  cards?: PlanCard[]
  pending?: boolean
}

export interface Milestone {
  id: string
  title: string
  why: string
  action: string
  section: PlanSectionId
  status: MilestoneStatus
  checkin?: string
  /** The fields below only exist when the milestone comes from the backend. */
  category?: string
  /** Share of required tasks done, 0-100. `null` = not applicable. */
  taskProgress?: number | null
  checkinPending?: boolean
  overdue?: boolean
}

export interface MentorScript {
  topic: string
  question: string
  prompts: string[]
}

export type SharedItemKind = 'question' | 'review' | 'update'

/** An item a household chose to share with its advisor. */
export interface SharedItem {
  kind: SharedItemKind
  text: string
  date: string
}

export interface AdvisorProfile {
  engagement: 'Active' | 'Invited'
  lastCheckin: string | null
  shared: SharedItem[]
}

export interface Family {
  id: FamilyId
  /** Case slug under `cases/` — the key used to look up plan data. */
  caseId: string
  household: string
  names: string
  surname: string
  initials: string
  score: number
  scoreNote: string
  facts: HouseholdFact[]
  challenge: string
  focusAreas: FocusArea[]
  nextStep: NextStep
  story: StoryChapter[]
  sections: Record<PlanSectionId, PlanSection>
  milestones: Milestone[]
  mentor: MentorScript
  checkinPriority: string
  advisor: AdvisorProfile
  /** Overrides the default link to the shared Sherpas plan. */
  planUrl?: string
  /** Set once the backend has produced the AI video for the story. */
  videoUrl?: string
}

export interface CheckinRecord {
  date: string
  summary: string
  shared: boolean
  note: string
}

/** Mutable demo state for one household. */
export interface FamilyState {
  milestones: Record<string, MilestoneStatus>
  checkins: CheckinRecord[]
  reviewRequested: boolean
  sharedItems: SharedItem[]
  watched: boolean
  nextCheckin: string
}

/** Where the user currently is inside the phone. */
export interface NavigationState {
  planSection: PlanSectionId
  planCard: string | null
  progressTab: ProgressTab
  openMilestone: string | null
  mentorTopic: string | null
  mentorFrom: FamilyScreen | null
}

/** Options accepted by the `go()` navigation helper. */
export interface NavigateOptions {
  section?: PlanSectionId
  card?: string
  tab?: ProgressTab
  open?: string
  topic?: string
  from?: FamilyScreen
}

/** Signature of the navigation helper exposed by the family provider. */
export type Navigate = (screen: FamilyScreen, options?: NavigateOptions) => void

