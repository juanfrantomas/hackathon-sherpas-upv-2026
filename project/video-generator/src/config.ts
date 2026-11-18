import 'dotenv/config';
import { z } from 'zod';

const EnvSchema = z.object({
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  HOST: z.string().default('127.0.0.1'),
  PUBLIC_BASE_URL: z.string().url().default('http://127.0.0.1:3000'),
  DEMO_MODE: z.enum(['true', 'false']).default('true').transform((v) => v === 'true'),

  LLM_BASE_URL: z.string().url().default('https://llm-hackathon.sherpaswealth.com/v1'),
  LLM_API_KEY: z.string().default(''),
  LLM_MODEL: z.string().min(1).default('deepseek-flash'),
  LLM_JSON_MODE: z.enum(['true', 'false']).default('false').transform((v) => v === 'true'),
  LLM_MAX_ATTEMPTS: z.coerce.number().int().min(1).max(2).default(1),

  AUDIO_MODE: z.enum(['none', 'elevenlabs', 'proxy']).default('none'),
  PROXY_TTS_MODEL: z.string().default('eleven-flash-v2.5'),
  PROXY_TTS_VOICE: z.string().default('alloy'),
  MUSIC_FILE: z.string().default(''),
  ELEVENLABS_API_KEY: z.string().default(''),
  ELEVENLABS_VOICE_ID: z.string().default(''),
  ELEVENLABS_TTS_MODEL: z.string().default('eleven_multilingual_v2'),
  GENERATE_MUSIC: z.enum(['true', 'false']).default('false').transform((v) => v === 'true'),

  MAX_VIDEO_SECONDS: z.coerce.number().int().min(5).max(180).default(180),
  VIDEO_FPS: z.coerce.number().int().refine((n) => n === 30, 'V1 currently supports only 30 fps').default(30),
});

export const config = EnvSchema.parse(process.env);

export function validateLiveConfig(): void {
  if (config.DEMO_MODE) return;
  if (!config.LLM_API_KEY.trim()) {
    throw new Error('Set LLM_API_KEY to the hackathon TEAM AI key in .env (not your MCP personal token).');
  }
  if (config.AUDIO_MODE === 'elevenlabs' && (!config.ELEVENLABS_API_KEY || !config.ELEVENLABS_VOICE_ID)) {
    throw new Error('Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID when AUDIO_MODE=elevenlabs.');
  }
  if (config.GENERATE_MUSIC && !config.MUSIC_FILE.trim() && config.AUDIO_MODE !== 'elevenlabs') {
    throw new Error('For proxy audio, GENERATE_MUSIC=true requires MUSIC_FILE pointing to an instrumental MP3.');
  }
}
