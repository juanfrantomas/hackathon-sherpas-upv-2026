import { config } from '../src/config.js';
import { createLlmClient } from '../src/llm/client.js';

async function main(): Promise<void> {
  const client = createLlmClient();
  console.log(`Checking ${config.LLM_MODEL} via ${config.LLM_BASE_URL}`);
  console.log('This test makes ONE billable request against the shared team credit.');
  const result = await client.chat.completions.create({
    model: config.LLM_MODEL,
    messages: [{ role: 'user', content: 'Reply with exactly one word: READY' }],
  });
  const answer = result.choices[0]?.message.content?.trim();
  if (!answer) throw new Error('Proxy returned no text. Check model compatibility.');
  console.log(`Model response: ${answer}`);
  console.log('Proxy connection succeeded. This does not yet verify the storyboard JSON format.');
}

main().catch((error: unknown) => {
  // Do not print credential-bearing request objects.
  const status = typeof error === 'object' && error !== null && 'status' in error ? String(error.status) : 'unknown';
  console.error(`LLM connection failed (HTTP status: ${status}). Verify URL, team key, model ID, balance, and proxy availability.`);
  process.exitCode = 1;
});
