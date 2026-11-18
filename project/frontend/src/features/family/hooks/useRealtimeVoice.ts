import { useCallback, useEffect, useRef, useState } from 'react'
import { BACKEND_LIVE_ENABLED, BACKEND_WS_URL } from '../services/config'
import type { VoiceState } from '../types'

/** The voice models the proxy offers. */
export const REALTIME_MODELS = [
  'gemini-3.8-live',
  'gpt-realtime-2.1-mini',
  'gpt-realtime-2.1',
] as const

export type RealtimeModel = (typeof REALTIME_MODELS)[number]

type Phase = 'idle' | 'connecting' | 'ready' | 'error'

export interface RealtimeSession {
  case_id: string
  model: string
  voice: string
  style_key: string
  style: string
  partner_mode: string | null
  is_couple: boolean
  couple_members: { key: string; name: string }[]
  topic: string | null
  message: string
}

/** One line of the conversation, as it is shown on screen. */
export interface TranscriptLine {
  id: number
  who: 'you' | 'mentor'
  text: string
  /** Still being said or heard. */
  live: boolean
  /** The household talked over the mentor. */
  cut: boolean
}

export interface ConnectOptions {
  model?: RealtimeModel
  style?: string | null
  partner?: string | null
  /** The milestone the household opened. */
  topic?: string | null
  /** The mentor opens with one sentence about the topic. */
  greet?: boolean
  /** A question to send as soon as the session is open. */
  firstQuestion?: string
}

export interface RealtimeVoiceValue {
  /** What the mentor is doing, derived from the real events of the session. */
  voice: VoiceState
  lines: TranscriptLine[]
  /** The plan section the mentor is reading, if any. */
  consulted: string | null
  session: RealtimeSession | null
  error: string | null
  /** Whether a session is open or opening. */
  active: boolean
  muted: boolean
  setMuted: (muted: boolean) => void
  connect: (options?: ConnectOptions) => Promise<void>
  disconnect: () => void
  sendText: (text: string) => void
  switchPartner: (partner: string) => void
}

const SAMPLE_RATE = 24000
/** Below this level the microphone is treated as silence. */
const VOICE_RMS_THRESHOLD = 0.01
/** Audio keeps flowing this long after the last sound, so the server hears the pause. */
const SILENCE_HANGOVER_MS = 1200

function toBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  const chunk = 0x8000
  for (let index = 0; index < bytes.length; index += chunk) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunk))
  }
  return btoa(binary)
}

/**
 * The live voice of the mentor.
 *
 * The browser records the microphone, sends it to the backend as PCM and plays
 * back the answer. The backend owns the session with the model, so no
 * credential reaches the browser. Everything the screen shows (state,
 * transcript, the section being read) comes from the events of that session.
 */
export function useRealtimeVoice(caseId: string): RealtimeVoiceValue {
  const [phase, setPhase] = useState<Phase>('idle')
  const [lines, setLines] = useState<TranscriptLine[]>([])
  const [consulted, setConsulted] = useState<string | null>(null)
  const [session, setSession] = useState<RealtimeSession | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [muted, setMutedState] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [thinking, setThinking] = useState(false)
  const [interrupted, setInterrupted] = useState(false)

  const socket = useRef<WebSocket | null>(null)
  const audioContext = useRef<AudioContext | null>(null)
  const microphone = useRef<MediaStream | null>(null)
  const processor = useRef<ScriptProcessorNode | null>(null)
  const sources = useRef<AudioBufferSourceNode[]>([])
  const playHead = useRef(0)
  const mutedRef = useRef(false)
  const lastVoice = useRef(0)
  const manualClose = useRef(false)
  const nextId = useRef(1)
  /** The line of the mentor being written, and the line of the household being heard. */
  const mentorLine = useRef<number | null>(null)
  const youLine = useRef<number | null>(null)
  const firstQuestion = useRef<string | null>(null)

  const patchLine = useCallback((id: number, patch: (line: TranscriptLine) => TranscriptLine) => {
    setLines((current) => current.map((line) => (line.id === id ? patch(line) : line)))
  }, [])

  const addLine = useCallback((who: TranscriptLine['who'], text = '', live = true) => {
    const id = nextId.current++
    setLines((current) => [...current, { id, who, text, live, cut: false }])
    return id
  }, [])

  const stopAudio = useCallback(() => {
    for (const source of sources.current) {
      try {
        source.stop()
      } catch {
        /* already stopped */
      }
    }
    sources.current = []
    playHead.current = audioContext.current ? audioContext.current.currentTime : 0
  }, [])

  const playChunk = useCallback((base64: string) => {
    const context = audioContext.current
    if (!context) return
    const binary = atob(base64)
    const count = binary.length >> 1
    const pcm = new Float32Array(count)
    for (let index = 0; index < count; index += 1) {
      let value = binary.charCodeAt(index * 2) | (binary.charCodeAt(index * 2 + 1) << 8)
      if (value >= 0x8000) value -= 0x10000
      pcm[index] = value / 0x8000
    }
    const buffer = context.createBuffer(1, count, SAMPLE_RATE)
    buffer.copyToChannel(pcm, 0)
    const source = context.createBufferSource()
    source.buffer = buffer
    source.connect(context.destination)
    playHead.current = Math.max(playHead.current, context.currentTime + 0.05)
    source.start(playHead.current)
    playHead.current += buffer.duration
    sources.current.push(source)
    source.onended = () => {
      sources.current = sources.current.filter((item) => item !== source)
    }
  }, [])

  const release = useCallback(() => {
    stopAudio()
    if (processor.current) {
      processor.current.onaudioprocess = null
      processor.current.disconnect()
      processor.current = null
    }
    if (microphone.current) {
      for (const track of microphone.current.getTracks()) track.stop()
      microphone.current = null
    }
    if (socket.current) {
      manualClose.current = true
      socket.current.close()
      socket.current = null
    }
    if (audioContext.current) {
      void audioContext.current.close()
      audioContext.current = null
    }
    mentorLine.current = null
    youLine.current = null
    firstQuestion.current = null
  }, [stopAudio])

  const resetTurnState = () => {
    setSpeaking(false)
    setThinking(false)
    setInterrupted(false)
  }

  /** Ends the session and returns to the idle state. */
  const disconnect = useCallback(() => {
    release()
    setPhase('idle')
    setSession(null)
    setLines([])
    setConsulted(null)
    setError(null)
    resetTurnState()
  }, [release])

  /** Closes the session after a failure, keeping the reason on screen. */
  const fail = useCallback(
    (message: string) => {
      release()
      setSession(null)
      resetTurnState()
      setError(message)
      setPhase('error')
    },
    [release],
  )

  const handleEvent = useCallback(
    (data: Record<string, unknown>) => {
      const kind = String(data.type ?? '')

      switch (kind) {
        case 'session_ready': {
          setSession(data as unknown as RealtimeSession)
          setPhase('ready')
          const question = firstQuestion.current
          firstQuestion.current = null
          if (question && socket.current?.readyState === WebSocket.OPEN) {
            youLine.current = null
            addLine('you', question, false)
            socket.current.send(JSON.stringify({ type: 'user_text', text: question }))
            setThinking(true)
          }
          return
        }
        case 'error':
          fail(String(data.message ?? 'The live voice failed'))
          return
        case 'tool_call':
          setConsulted(typeof data.section === 'string' ? data.section : null)
          return
        case 'input_audio_buffer.speech_started': {
          // The household talks: whatever the mentor was saying stops at once.
          stopAudio()
          if (mentorLine.current !== null) {
            patchLine(mentorLine.current, (line) => ({ ...line, live: false, cut: true }))
            mentorLine.current = null
            setInterrupted(true)
          }
          setSpeaking(false)
          setThinking(false)
          youLine.current = addLine('you')
          return
        }
        case 'input_audio_buffer.speech_stopped':
          setInterrupted(false)
          setThinking(true)
          return
        case 'conversation.item.input_audio_transcription.completed': {
          const text = typeof data.transcript === 'string' ? data.transcript.trim() : ''
          if (youLine.current !== null) {
            patchLine(youLine.current, (line) => ({ ...line, text, live: false }))
            youLine.current = null
          } else if (text) {
            addLine('you', text, false)
          }
          return
        }
        case 'response.output_audio_transcript.delta':
        case 'response.audio_transcript.delta': {
          if (typeof data.delta !== 'string') return
          setThinking(false)
          setInterrupted(false)
          const delta = data.delta
          if (mentorLine.current === null) mentorLine.current = addLine('mentor')
          patchLine(mentorLine.current, (line) => ({ ...line, text: line.text + delta }))
          return
        }
        case 'response.output_audio.delta':
        case 'response.audio.delta':
          if (typeof data.delta !== 'string') return
          setThinking(false)
          setInterrupted(false)
          setSpeaking(true)
          playChunk(data.delta)
          return
        case 'response.done':
        case 'response.output_audio.done': {
          if (mentorLine.current !== null) {
            patchLine(mentorLine.current, (line) => ({ ...line, live: false }))
            mentorLine.current = null
          }
          // Audio already queued keeps playing; the state follows the queue.
          const context = audioContext.current
          const remaining = context ? Math.max(0, playHead.current - context.currentTime) : 0
          window.setTimeout(() => setSpeaking(false), remaining * 1000)
          setThinking(false)
          setConsulted(null)
          // A household line the model never transcribed would stay empty.
          setLines((current) => current.filter((line) => line.who !== 'you' || line.text || line.live))
          return
        }
        default:
      }
    },
    [addLine, fail, patchLine, playChunk, stopAudio],
  )

  const connect = useCallback(
    async (options: ConnectOptions = {}) => {
      if (!BACKEND_LIVE_ENABLED) {
        fail('The mentor needs the backend. Set VITE_BACKEND_API_URL.')
        return
      }
      release()
      manualClose.current = false
      setPhase('connecting')
      setError(null)
      setLines([])
      setConsulted(null)
      resetTurnState()
      firstQuestion.current = options.firstQuestion ?? null

      try {
        const context = new AudioContext({ sampleRate: SAMPLE_RATE })
        audioContext.current = context
        await context.resume()
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            channelCount: 1,
          },
        })
        microphone.current = stream

        const source = context.createMediaStreamSource(stream)
        // Only speech is sent (plus a short tail of silence so the server can
        // detect the end of the turn). Streaming ambient noise would keep the
        // model from answering typed questions.
        const node = context.createScriptProcessor(2048, 1, 1)
        source.connect(node)
        node.connect(context.destination)
        node.onaudioprocess = (event) => {
          const ws = socket.current
          if (mutedRef.current || !ws || ws.readyState !== WebSocket.OPEN) return
          const input = event.inputBuffer.getChannelData(0)
          const pcm = new Int16Array(input.length)
          let sum = 0
          for (let index = 0; index < input.length; index += 1) {
            const sample = Math.max(-1, Math.min(1, input[index]))
            pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
            sum += sample * sample
          }
          const now = performance.now()
          if (Math.sqrt(sum / input.length) > VOICE_RMS_THRESHOLD) lastVoice.current = now
          if (now - lastVoice.current > SILENCE_HANGOVER_MS) return
          ws.send(
            JSON.stringify({ type: 'input_audio_buffer.append', audio: toBase64(pcm.buffer) }),
          )
        }
        processor.current = node

        const query = new URLSearchParams({
          model: options.model ?? REALTIME_MODELS[0],
          style: options.style ?? 'auto',
          partner: options.partner ?? 'both',
        })
        if (options.topic) query.set('topic', options.topic)
        if (options.greet && options.topic) query.set('greet', '1')

        const ws = new WebSocket(
          `${BACKEND_WS_URL}/api/voice/ws/${encodeURIComponent(caseId)}?${query}`,
        )
        socket.current = ws

        ws.onmessage = (event) => {
          try {
            handleEvent(JSON.parse(String(event.data)) as Record<string, unknown>)
          } catch {
            /* a message that is not JSON carries nothing for the screen */
          }
        }
        ws.onerror = () => {
          if (socket.current === ws) fail('The live voice could not be opened.')
        }
        ws.onclose = (event) => {
          if (socket.current !== ws || manualClose.current) return
          fail(
            event.reason
              ? `The live voice closed: ${event.reason}`
              : 'The live voice connection was closed.',
          )
        }
      } catch (cause) {
        const denied = cause instanceof DOMException && cause.name === 'NotAllowedError'
        fail(
          denied
            ? 'The microphone is blocked. Allow it in the browser to talk to your mentor.'
            : cause instanceof Error
              ? cause.message
              : 'The microphone is not available.',
        )
      }
    },
    [caseId, fail, handleEvent, release],
  )

  const sendText = useCallback(
    (text: string) => {
      const clean = text.trim()
      if (!clean || socket.current?.readyState !== WebSocket.OPEN) return
      stopAudio()
      mentorLine.current = null
      addLine('you', clean, false)
      setSpeaking(false)
      setInterrupted(false)
      setThinking(true)
      socket.current.send(JSON.stringify({ type: 'user_text', text: clean }))
    },
    [addLine, stopAudio],
  )

  const switchPartner = useCallback((partner: string) => {
    if (socket.current?.readyState !== WebSocket.OPEN) return
    socket.current.send(JSON.stringify({ type: 'switch_partner', partner }))
  }, [])

  const setMuted = useCallback((value: boolean) => {
    mutedRef.current = value
    setMutedState(value)
  }, [])

  // A different household, or leaving the screen, ends the session.
  useEffect(() => () => disconnect(), [caseId, disconnect])

  let voice: VoiceState
  if (phase === 'error') voice = 'error'
  else if (phase === 'idle') voice = 'ready'
  else if (phase === 'connecting') voice = 'thinking'
  else if (interrupted) voice = 'interrupted'
  else if (speaking) voice = 'speaking'
  else if (thinking) voice = 'thinking'
  else if (muted) voice = 'muted'
  else voice = 'listening'

  return {
    voice,
    lines,
    consulted,
    session,
    error,
    active: phase === 'connecting' || phase === 'ready',
    muted,
    setMuted,
    connect,
    disconnect,
    sendText,
    switchPartner,
  }
}
