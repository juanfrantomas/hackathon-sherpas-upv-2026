import { useContext } from 'react'
import { MentorContext, type MentorSession } from './mentorContext'

/** The mentor conversation: what is being asked, and what is being said. */
export function useMentorSession(): MentorSession {
  const value = useContext(MentorContext)
  if (!value) {
    throw new Error('useMentorSession must be used inside a MentorProvider')
  }
  return value
}
