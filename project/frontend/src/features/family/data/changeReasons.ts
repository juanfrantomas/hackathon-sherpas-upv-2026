/** Reasons a household can report when something material has changed. */
export const CHANGE_REASONS = [
  'Job or income',
  'Family',
  'Home',
  'Health',
  'Something else',
] as const

export type ChangeReason = (typeof CHANGE_REASONS)[number]
