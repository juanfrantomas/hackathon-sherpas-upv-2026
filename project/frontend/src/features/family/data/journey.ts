import type { FamilyScreen, NavigateOptions } from '../types'

export interface JourneyStep {
  n: number
  id: string
  label: string
  screen: FamilyScreen
  opts?: NavigateOptions
}

/**
 * The prototype's left-hand rail: the eight steps of the demo journey.
 * Selecting a step drives the phone to the matching screen.
 */
export const JOURNEY: JourneyStep[] = [
  { n: 1, id: 'welcome', label: 'Welcome', screen: 'welcome' },
  { n: 2, id: 'story', label: 'Financial story', screen: 'story' },
  { n: 3, id: 'home', label: 'Home dashboard', screen: 'home' },
  { n: 4, id: 'mentor', label: 'AI mentor · voice', screen: 'mentor' },
  { n: 5, id: 'plan', label: 'My financial plan', screen: 'plan' },
  {
    n: 6,
    id: 'milestones',
    label: 'Goals & milestones',
    screen: 'progress',
    opts: { tab: 'milestones' },
  },
  { n: 7, id: 'checkin', label: 'Check-in', screen: 'checkin' },
  {
    n: 8,
    id: 'journey',
    label: 'Progress overview',
    screen: 'progress',
    opts: { tab: 'journey' },
  },
]
