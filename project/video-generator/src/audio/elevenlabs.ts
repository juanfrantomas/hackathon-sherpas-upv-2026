import { writeFile } from 'node:fs/promises';
import { config } from '../config.js';

export type SpeechResult = { durationSeconds: number; filename: string };

function friendlyApiError(provider: string, status: number): Error {
  // Do not include response bodies or secrets in client-visible errors.
  return new Error(`${provider} request failed with HTTP ${status}. Check your key, quota, and model access.`);
}

export async function synthesizeSpeech(text: string, filename: string): Promise<SpeechResult> {
  const url = `https://api.elevenlabs.io/v1/text-to-speech/${encodeURIComponent(config.ELEVENLABS_VOICE_ID)}/with-timestamps?output_format=mp3_44100_128`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'xi-api-key': config.ELEVENLABS_API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, model_id: config.ELEVENLABS_TTS_MODEL }),
    signal: AbortSignal.timeout(120_000),
  });
  if (!response.ok) throw friendlyApiError('ElevenLabs speech', response.status);
  const data = await response.json() as {
    audio_base64?: string;
    alignment?: { character_end_times_seconds?: number[] };
    normalized_alignment?: { character_end_times_seconds?: number[] };
  };
  if (!data.audio_base64) throw new Error('ElevenLabs speech returned no audio.');
  const ends = data.alignment?.character_end_times_seconds ?? data.normalized_alignment?.character_end_times_seconds;
  const durationSeconds = ends?.at(-1);
  if (!durationSeconds || durationSeconds <= 0) throw new Error('ElevenLabs speech returned no valid timing.');
  await writeFile(filename, Buffer.from(data.audio_base64, 'base64'));
  return { filename, durationSeconds };
}

export async function synthesizeMusic(durationSeconds: number, filename: string): Promise<void> {
  const requestedMilliseconds = Math.round(durationSeconds * 1000);
  const response = await fetch('https://api.elevenlabs.io/v1/music?output_format=mp3_44100_128', {
    method: 'POST',
    headers: { 'xi-api-key': config.ELEVENLABS_API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model_id: 'music_v2_5',
      prompt: 'Warm, professional understated ambient instrumental music, quiet piano and soft electronic textures, steady and reassuring, no vocals, suitable for narrated financial education. Avoid dramatic changes.',
      music_length_ms: requestedMilliseconds,
      force_instrumental: true,
    }),
    signal: AbortSignal.timeout(150_000),
  });
  if (!response.ok) throw friendlyApiError('ElevenLabs music', response.status);
  await writeFile(filename, Buffer.from(await response.arrayBuffer()));
}
