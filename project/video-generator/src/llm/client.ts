import OpenAI from 'openai';
import { config } from '../config.js';

/** OpenAI SDK used as an HTTP client for the team's OpenAI-compatible proxy. */
export function createLlmClient(): OpenAI {
  if (!config.LLM_API_KEY.trim()) {
    throw new Error('Missing LLM_API_KEY. Paste the TEAM AI key into .env.');
  }
  return new OpenAI({
    apiKey: config.LLM_API_KEY,
    baseURL: config.LLM_BASE_URL,
    timeout: 90_000,
    maxRetries: 0, // Don't silently repeat paid requests against shared credits.
  });
}
