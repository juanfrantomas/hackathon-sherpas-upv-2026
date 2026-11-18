import 'dotenv/config';
import path from 'node:path';
import { mkdir, writeFile } from 'node:fs/promises';
import OpenAI from 'openai';
import { parseFile } from 'music-metadata';

async function main(): Promise<void> {
  const key = process.env.LLM_API_KEY;
  if (!key) throw new Error('Set LLM_API_KEY in .env (team key, NOT the MCP token).');
  const baseURL = process.env.LLM_BASE_URL ?? 'https://llm-hackathon.sherpaswealth.com/v1';
  const model = process.env.PROXY_TTS_MODEL ?? 'eleven-flash-v2.5';
  const voice = process.env.PROXY_TTS_VOICE ?? 'alloy';
  const client = new OpenAI({ apiKey: key, baseURL, maxRetries: 0, timeout: 45_000 });

  console.log(`Testing proxy TTS model '${model}' with a short sentence.`);
  console.log('This request may use a small amount of team credit.');
  try {
    const response = await client.audio.speech.create({
      model,
      voice,
      input: 'Hello. This is a short test of our financial video narration.',
      response_format: 'mp3',
    });
    const audio = Buffer.from(await response.arrayBuffer());
    await mkdir('output', { recursive: true });
    const filename = path.resolve('output/proxy-tts-test.mp3');
    await writeFile(filename, audio);
    const { format } = await parseFile(filename, { duration: true });
    if (!format.duration || format.duration <= 0) throw new Error('The response was not a playable MP3.');
    console.log(`SUCCESS: ${filename}`);
    console.log(`Audio duration: ${format.duration.toFixed(2)}s`);
  } catch (error: unknown) {
    const status = typeof error === 'object' && error !== null && 'status' in error
      ? String(error.status)
      : 'unknown';
    console.error(`TTS test failed. HTTP status: ${status}.`);
    console.error('Possible causes: /audio/speech is unsupported, the model or voice ID differs, or the team quota is exhausted.');
    console.error('Ask organizers for the TTS endpoint, request body, and supported voices.');
    process.exitCode = 1;
  }
}

void main();
