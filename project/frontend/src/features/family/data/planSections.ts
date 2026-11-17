import type { PlanSectionId } from '../types'

export interface PlanSectionLink {
  id: PlanSectionId
  label: string
}

/** The six sections of a Sherpas financial plan, in plan order. */
export const PLAN_SECTIONS: PlanSectionLink[] = [
  { id: 'summary', label: 'Summary' },
  { id: 'retirement', label: 'Retirement & Goals' },
  { id: 'assets', label: 'Assets & Investments' },
  { id: 'debt', label: 'Debt management' },
  { id: 'savings', label: 'Savings & Expenses' },
  { id: 'protection', label: 'Insurance & Protection' },
]

/** Shown next to the score and on the plan screen. */
export const PLAN_DISCLAIMER =
  'Rules-based diagnostic from provided data and assumptions; may vary with inputs.'
