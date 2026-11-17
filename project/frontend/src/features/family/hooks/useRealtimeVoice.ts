import { useCallback, useEffect, useRef, useState } from 'react'
import { BACKEND_LIVE_ENABLED, BACKEND_WS_URL } from '../services/config'

/** The voice models the proxy offers. */
export const REALTIME_MODELS = [
  'gemini-3.8-live',
  'gpt-realtime-2.1-mini',
  'gpt-realtime-2.1',
] as const

export type RealtimeModel = (typeof REALTIME_MODELS)[number]

export type RealtimeState = 'idle' | 'connecting' | 'ready' | 'error'

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
  score: { published_score?: number; band?: string } | null
  message: string
}

export interface RealtimeVoiceValue {
  state: RealtimeState
  /** The transcript of what the mentor is saying. */
  transcript: string
  /** Whether the microphone is picking up sound. */
  listening: boolean
  session: RealtimeSession | null
  error: string | null
  connect: (options?: {
    model?: RealtimeModel
    style?: string | null
    partner?: string | null
    topic?: string | null
  }) => Promise<void>
  disconnect: () => void
  sendText: (text: string) => void
  switchPartner: (partner: string) => void
}

const SAMPLE_RATE = 24000
const SILENCE_HANGOVER_MS = 1200
const VOICE_RMS_THRESHOLD = 0.01

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
 * The browser records the microphone, sends it to the backend as PCM and
 * plays back the answer.  The backend owns the session with the model, so no
 * credential ever reaches the browser.
 */
export function useRealtimeVoice(caseId: string): RealtimeVoiceValue {
  const [state, setState] = useState<RealtimeState>('idle')
  const [transcript, setTranscript] = useState('')
  const [listening, setListening] = useState(false)
  const [session, setSession] = useState<RealtimeSession | null>(null)
  const [error, setError] = useState<string | null>(null)

  const socket = useRef<WebSocket | null>(null)
  const audioContext = useRef<AudioContext | null>(null)
  const microphone = useRef<MediaStream | null>(null)
  const processor = useRef<ScriptProcessorNode | null>(null)
  const sources = useRef<AudioBufferSourceNode[]>([])
  const playHead = useRef(0)
  const lastVoice = useRef(0)

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

  const disconnect = useCallback(() => {
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
      socket.current.close()
      socket.current = null
    }
    if (audioContext.current) {
      void audioContext.current.close()
      audioContext.current = null
    }
    setState('idle')
    setSession(null)
    setTranscript('')
    setListening(false)
  }, [stopAudio])

  const connect = useCallback(
    async (options: {
      model?: RealtimeModel
      style?: string | null
      partner?: string | null
      topic?: string | null
    } = {}) => {
      if (!BACKEND_LIVE_ENABLED) return
      setState('connecting')
      setError(null)
      setTranscript('')

      try {
        const context = new AudioContext({ sampleRate: SAMPLE_RATE })
        audioContext.current = context
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
        const node = context.createScriptProcessor(2048, 1, 1)
        source.connect(node)
        node.connect(context.destination)
        node.onaudioprocess = (event) => {
          const input = event.inputBuffer.getChannelData(0)
          const pcm = new Int16Array(input.length)
          let sum = 0
          for (let index = 0; index < input.length; index += 1) {
            const sample = Math.max(-1, Math.min(1, input[index]))
            pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
            sum += sample * sample
          }
          const rms = Math.sqrt(sum / input.length)
          setListening(rms > VOICE_RMS_THRESHOLD)

          const now = performance.now()
          if (rms > VOICE_RMS_THRESHOLD) lastVoice.current = now
          if (
            socket.current &&
            socket.current.readyState === WebSocket.OPEN &&
            now - lastVoice.current <= SILENCE_HANGOVER_MS
          ) {
            socket.current.send(
              JSON.stringify({
                type: 'input_audio_buffer.append',
                audio: toBase64(pcm.buffer),
              }),
            )
          }
        }
        processor.current = node

        const query = new URLSearchParams({
          model: options.model ?? REALTIME_MODELS[0],
          style: options.style ?? 'auto',
          partner: options.partner ?? 'both',
        })
        if (options.topic) query.set('topic', options.topic)

        const url = `${BACKEND_WS_URL}/api/voice/ws/${encodeURIComponent(caseId)}?${query}`
        const ws = new WebSocket(url)
        socket.current = ws

        ws.onmessage = (event) => {
          let data: Record<string, unknown>
          try {
            data = JSON.parse(String(event.data)) as Record<string, unknown>
          } catch {
            return
          }
          const kind = String(data.type ?? '')
          if (kind === 'session_ready') {
            setSession(data as unknown as RealtimeSession)
            setState('ready')
          } else if (kind === 'error') {
            setError(String(data.message ?? 'The live voice failed'))
            setState('error')
          } else if (kind.includes('transcript') && typeof data.delta === 'string') {
            setTranscript((current) => current + data.delta)
          } else if (
            (kind === 'response.output_audio.delta' ||
              kind === 'response.audio.delta') &&
            typeof data.delta === 'string'
          ) {
            playChunk(data.delta)
          }
        }
        ws.onerror = () => {
          setError('The live voice could not be opened')
          setState('error')
        }
        ws.onclose = () => {
          if (socket.current === ws) setState('idle')
        }
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'The microphone is not available')
        setState('error')
        disconnect()
      }
    },
    [caseId, disconnect, playChunk],
  )

  const sendText = useCallback((text: string) => {
    if (socket.current?.readyState !== WebSocket.OPEN) return
    socket.current.send(JSON.stringify({ type: 'user_text', text }))
  }, [])

  const switchPartner = useCallback((partner: string) => {
    if (socket.current?.readyState !== WebSocket.OPEN) return
    socket.current.send(JSON.stringify({ type: 'switch_partner', partner }))
  }, [])

  useEffect(() => () => disconnect(), [disconnect])

  return {
    state,
    transcript,
    listening,
    session,
    error,
    connect,
    disconnect,
    sendText,
    switchPartner,
  }
}
