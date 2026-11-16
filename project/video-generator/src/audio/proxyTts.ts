import { writeFile } from 'node:fs/promises';
import { parseFile } from 'music-metadata';
import { config } from '../config.js';
import { createLlmClient } from '../llm/client.js';
import type { SpeechResult } from './elevenlabs.js';

/**
 * Assumes Sherpaswealth implements the OpenAI-compatible POST /v1/audio/speech.
 * This endpoint has NOT been independently verified. Test with the short
 * scripts/check-proxy-tts.ts before enabling it for full video jobs.
 */
export async function synthesizeProxySpeech(text: string, filename: string): Promise<SpeechResult> {
  const client = createLlmClient();
  const audioResponse = await client.audio.speech.create({
    model: config.PROXY_TTS_MODEL,
    voice: config.PROXY_TTS_VOICE,
    input: text,
    response_format: 'mp3',
  });

  const bytes = Buffer.from(await audioResponse.arrayBuffer());
  if (bytes.length < 100) {
    throw new Error('The proxy TTS response was too small to contain valid audio.');
  }
  await writeFile(filename, bytes);

  // The OpenAI speech route returns audio, unlike ElevenLabs with-timestamps.
  // Measure the actual file duration instead of estimating speech speed.
  const { format } = await parseFile(filename, { duration: true });
  const durationSeconds = format.duration;
  if (!durationSeconds || !Number.isFinite(durationSeconds) || durationSeconds <= 0) {
    throw new Error('Cannot read the proxy narration duration. Check its MP3 format.');
  }
  return { filename, durationSeconds };
}
