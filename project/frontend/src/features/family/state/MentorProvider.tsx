import { useCallback, useMemo, type ReactNode } from 'react'
import { useFamilyData, useNavigation } from './useFamily'
import { useRealtimeVoice } from '../hooks/useRealtimeVoice'
import { MentorContext, type MentorSession } from './mentorContext'

/**
 * Owns the live conversation with the mentor. The only channel is the
 * backend's WebSocket: there is no scripted or simulated answer.
 */
export function MentorProvider({ children }: { children: ReactNode }) {
  const { family } = useFamilyData()
  const { nav } = useNavigation()
  const live = useRealtimeVoice(family.caseId)

  const topic = nav.mentorTopic
  const { connect, sendText, active } = live

  const start = useCallback(() => {
    void connect({ topic, greet: Boolean(topic) })
  }, [connect, topic])

  const ask = useCallback(
    (question: string) => {
      if (active) sendText(question)
      else void connect({ topic, firstQuestion: question })
    },
    [active, connect, sendText, topic],
  )

  const value = useMemo<MentorSession>(
    () => ({ ...live, start, ask }),
    [live, start, ask],
  )

  return <MentorContext.Provider value={value}>{children}</MentorContext.Provider>
}
