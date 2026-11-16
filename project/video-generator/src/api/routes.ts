import { randomUUID } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import path from 'node:path';
import type { FastifyInstance } from 'fastify';
import { ZodError } from 'zod';
import { config } from '../config.js';
import { createFactRegistry } from '../financial/factRegistry.js';
import { getJob, submitJob } from '../jobs/runner.js';
import { generateStoryboard } from '../storytelling/generate.js';
import { validateDocuments } from '../validation/documents.js';

const uploadFields = ['financialHealth', 'investmentAnalysis', 'persona'] as const;
const idRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function registerRoutes(app: FastifyInstance): Promise<void> {
  app.get('/health', async () => ({ status: 'ok', demoMode: config.DEMO_MODE }));

  app.post('/api/v1/videos', async (request, reply) => {
    const contentType = request.headers['content-type'] ?? '';
    if (!contentType.includes('multipart/form-data')) {
      return reply.code(415).send({ error: 'Use multipart/form-data.' });
    }
    const files = new Map<string, Buffer>();
    try {
      for await (const part of request.parts()) {
        if (part.type !== 'file') continue;
        if (!uploadFields.includes(part.fieldname as typeof uploadFields[number])) {
          return reply.code(400).send({ error: `Unexpected file field: ${part.fieldname}` });
        }
        if (files.has(part.fieldname)) return reply.code(400).send({ error: `Duplicate file field: ${part.fieldname}` });
        files.set(part.fieldname, await part.toBuffer());
      }
      if (uploadFields.some((name) => !files.has(name))) {
        return reply.code(400).send({ error: 'Expected exactly financialHealth, investmentAnalysis, and persona file fields.' });
      }
      const json = (name: string) => JSON.parse(files.get(name)!.toString('utf8')) as unknown;
      const input = validateDocuments(json('financialHealth'), json('investmentAnalysis'), files.get('persona')!.toString('utf8'));
      const facts = createFactRegistry(input);
      // The TEAM LLM key stays on the server in .env; callers upload only the three documents.
      const storyboard = await generateStoryboard(input, facts);
      const jobId = randomUUID();
      const job = submitJob(jobId, storyboard, facts);
      return reply.code(202).send({ jobId, status: job.status, statusUrl: `/api/v1/videos/${jobId}` });
    } catch (error) {
      if (error instanceof ZodError) return reply.code(422).send({ error: 'Invalid financial input or storyboard', issues: error.issues.map((i) => ({ path: i.path.join('.'), message: i.message })) });
      if (error instanceof SyntaxError) return reply.code(400).send({ error: 'One of the JSON files contains invalid JSON.' });
      if (error instanceof Error && /file.*too large|too many files|request file too large/i.test(error.message)) {
        return reply.code(413).send({ error: 'File count or size limit exceeded.' });
      }
      const message = error instanceof Error ? error.message : '';
      if (/Missing\/invalid number|Conflicting|must describe|cannot be empty|too large|Unknown financial|numeric text/i.test(message)) {
        return reply.code(422).send({ error: message });
      }
      request.log.error({ err: error instanceof Error ? error.name : 'Error' }, 'Video job submission failed');
      return reply.code(502).send({ error: 'Storyboard generation failed. Check the team proxy key, model access, credit balance, and input validity.' });
    }
  });

  app.get<{ Params: { jobId: string } }>('/api/v1/videos/:jobId', async (request, reply) => {
    if (!idRegex.test(request.params.jobId)) return reply.code(404).send({ error: 'Job not found.' });
    const job = getJob(request.params.jobId);
    if (!job) return reply.code(404).send({ error: 'Job not found.' });
    return {
      jobId: job.jobId, status: job.status, progress: job.progress,
      warnings: job.warnings,
      ...(job.status === 'failed' ? { error: job.error } : {}),
      ...(job.status === 'completed' ? { downloadUrl: `/api/v1/videos/${job.jobId}/download` } : {}),
    };
  });

  app.get<{ Params: { jobId: string } }>('/api/v1/videos/:jobId/download', async (request, reply) => {
    if (!idRegex.test(request.params.jobId)) return reply.code(404).send({ error: 'Job not found.' });
    const job = getJob(request.params.jobId);
    if (!job) return reply.code(404).send({ error: 'Job not found.' });
    if (job.status !== 'completed' || !job.outputFile) return reply.code(409).send({ error: 'Video is not ready.' });
    const { size } = await stat(job.outputFile);
    return reply.type('video/mp4').header('Content-Length', size)
      .header('Content-Disposition', 'attachment; filename="financial-story.mp4"')
      .send(createReadStream(job.outputFile));
  });

  // Local-only asset serving for the Remotion Chromium renderer. Do not deploy publicly unchanged.
  app.get<{ Params: { jobId: string; filename: string } }>('/internal-assets/:jobId/:filename', async (request, reply) => {
    const { jobId, filename } = request.params;
    if (!idRegex.test(jobId) || !/^(?:scene-\d+|music)\.mp3$/.test(filename)) {
      return reply.code(404).send({ error: 'Asset not found.' });
    }
    const fullPath = path.resolve('output', jobId, filename);
    try { await stat(fullPath); }
    catch { return reply.code(404).send({ error: 'Asset not found.' }); }
    return reply.type('audio/mpeg').send(createReadStream(fullPath));
  });
}
