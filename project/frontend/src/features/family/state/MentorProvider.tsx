import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useFamilyData, useNavigation } from './useFamily'
import { askMentor, audioUrl } from '../services/mentorApi'
import {
  MENTOR_FALLBACK,
  MENTOR_LIVE_ENABLED,
  MENTOR_MIN_THINKING_MS,
} from '../services/config'
import { MentorContext, type MentorSession } from './mentorContext'

/**
 * Owns the mentor conversation: which question is in play, which answer is
 * being spoken, and the transitions between voice states.
 *
 * With no backend configured the session is fully scripted and behaves exactly
 * like the prototype did.
 */
export function MentorProvider({ children }: { children: ReactNode }) {
  const { family } = useFamilyData()
  const { voice, setVoice } = useNavigation()

  const scriptedQuestion = family.mentor.question
  const scriptedAnswer = family.mentor.answer

  const [question, setQuestion] = useState(scriptedQuestion)
  const [liveAnswer, setLiveAnswer] = useState<string | null>(null)
  const [liveAudio, setLiveAudio] = useState<string | null>(null)
  const [live, setLive] = useState(false)
  const [pending, setPending] = useState(false)

  const requestId = useRef(0)
  const thinkingSince = useRef(0)

  // A new household means a new conversation: reset during render, so the
  // transcript never shows the previous household for a frame.
  const [trackedFamily, setTrackedFamily] = useState(family.id)
  if (trackedFamily !== family.id) {
    setTrackedFamily(family.id)
    setQuestion(scriptedQuestion)
    setLiveAnswer(null)
    setLiveAudio(null)
    setLive(false)
    setPending(false)
  }

  // Discard any answer still in flight for the previous household.
  useEffect(() => {
    requestId.current += 1
  }, [family.id])

  const runRequest = useCallback(
    async (asked: string) => {
      if (!MENTOR_LIVE_ENABLED) return
      const id = ++requestId.current
      setPending(true)
      try {
        const response = await askMentor({ caseId: family.caseId, question: asked })
        if (id !== requestId.current) return
        setLiveAnswer(response.answer)
        setLiveAudio(audioUrl(response.audio_url))
        setLive(true)
      } catch {
        if (id !== requestId.current) return
        setLive(false)
        if (MENTOR_FALLBACK === 'error') {
          setLiveAnswer(null)
          setVoice('error')
        } else {
          // Fall back to the scripted exchange rather than showing an error.
          // The scripted answer still counts as "ready", so the conversation
          // keeps moving instead of stalling in the thinking state.
          setQuestion(scriptedQuestion)
          setLiveAnswer(scriptedAnswer)
        }
      } finally {
        if (id === requestId.current) setPending(false)
      }
    },
    [family.caseId, scriptedQuestion, scriptedAnswer, setVoice],
  )

  const ask = useCallback(
    (asked?: string) => {
      // Without a backend the mentor stays scripted, exactly as in the
      // prototype: which prompt was tapped makes no difference.
      const next = MENTOR_LIVE_ENABLED
        ? asked?.trim() || scriptedQuestion
        : scriptedQuestion
      setQuestion(next)
      setLiveAnswer(null)
      setLive(false)
      setVoice('listening')
      void runRequest(next)
    },
    [scriptedQuestion, runRequest, setVoice],
  )

  const advance = useCallback(() => {
    switch (voice) {
      case 'ready':
      case 'muted':
      case 'error':
        ask()
        return
      case 'listening':
        setVoice('thinking')
        return
      case 'thinking':
        setVoice('speaking')
        return
      case 'speaking':
        setVoice('interrupted')
        return
      case 'interrupted':
        setVoice('thinking')
        return
    }
  }, [voice, ask, setVoice])

  const setMuted = useCallback(
    (muted: boolean) => setVoice(muted ? 'muted' : 'ready'),
    [setVoice],
  )

  const retry = useCallback(() => {
    setLiveAnswer(null)
    setLive(false)
    setVoice('listening')
    void runRequest(question)
  }, [question, runRequest, setVoice])

  const end = useCallback(() => {
    requestId.current += 1
    setPending(false)
    setLiveAnswer(null)
    setLive(false)
    setVoice('ready')
  }, [setVoice])

  // Track how long the mentor has been "thinking", so the state stays visible.
  useEffect(() => {
    if (voice === 'thinking') {
      if (thinkingSince.current === 0) thinkingSince.current = Date.now()
    } else {
      thinkingSince.current = 0
    }
  }, [voice])

  // Move from "thinking" to "speaking" as soon as there is something to say.
  useEffect(() => {
    if (voice !== 'thinking') return
    const answerReady = liveAnswer ?? (MENTOR_LIVE_ENABLED ? null : scriptedAnswer)
    if (!answerReady) return
    const waited = Date.now() - thinkingSince.current
    const remaining = Math.max(0, MENTOR_MIN_THINKING_MS - waited)
    const timer = setTimeout(() => setVoice('speaking'), remaining)
    return () => clearTimeout(timer)
  }, [voice, liveAnswer, scriptedAnswer, setVoice])

  const value = useMemo<MentorSession>(
    () => ({
      question,
      answer: liveAnswer ?? scriptedAnswer,
      audio: liveAudio,
      live,
      liveEnabled: MENTOR_LIVE_ENABLED,
      pending,
      ask,
      advance,
      setMuted,
      retry,
      end,
    }),
    [
      question,
      liveAnswer,
      liveAudio,
      scriptedAnswer,
      live,
      pending,
      ask,
      advance,
      setMuted,
      retry,
      end,
    ],
  )

  return <MentorContext.Provider value={value}>{children}</MentorContext.Provider>
}
