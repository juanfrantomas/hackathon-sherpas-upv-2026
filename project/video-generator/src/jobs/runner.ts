import path from 'node:path';
import { copyFile, mkdir } from 'node:fs/promises';
import { config } from '../config.js';
import { synthesizeMusic, synthesizeSpeech } from '../audio/elevenlabs.js';
import { synthesizeProxySpeech } from '../audio/proxyTts.js';
import type { FactRegistry } from '../financial/factRegistry.js';
import { formatFact } from '../financial/factRegistry.js';
import type { Storyboard } from '../storytelling/storyboard.js';
import { renderNarration } from '../storytelling/storyboard.js';
import { renderVideo } from '../video/render.js';
import type { RenderScene, VideoProps } from '../video/types.js';

export type JobStatus = 'queued' | 'generating_audio' | 'generating_music' | 'rendering' | 'completed' | 'failed';
export type Job = {
  jobId: string;
  status: JobStatus;
  progress: number;
  error?: string;
  warnings: string[];
  createdAt: string;
  outputFile?: string;
};

const jobs = new Map<string, Job>();
const pending: Array<() => Promise<void>> = [];
let running = false;

export function getJob(id: string): Job | undefined { return jobs.get(id); }

export function submitJob(jobId: string, storyboard: Storyboard, facts: FactRegistry): Job {
  const job: Job = { jobId, status: 'queued', progress: 0, warnings: [], createdAt: new Date().toISOString() };
  jobs.set(jobId, job);
  pending.push(async () => {
    try { await runJob(job, storyboard, facts); }
    catch (error) {
      job.status = 'failed';
      job.error = error instanceof Error ? error.message : 'Unexpected generation failure.';
    }
  });
  void drainQueue();
  return job;
}

async function drainQueue(): Promise<void> {
  if (running) return;
  running = true;
  try {
    while (pending.length) {
      const next = pending.shift()!;
      await next();
    }
  } finally { running = false; }
}

async function runJob(job: Job, storyboard: Storyboard, facts: FactRegistry): Promise<void> {
  const folder = path.resolve('output', job.jobId);
  await mkdir(folder, { recursive: true });
  job.status = 'generating_audio';
  job.progress = 10;
  const scenes: RenderScene[] = [];
  for (let index = 0; index < storyboard.scenes.length; index++) {
    const storyScene = storyboard.scenes[index]!;
    const narration = renderNarration(storyScene, facts);
    let seconds: number;
    let audioUrl: string | null = null;
    if (config.DEMO_MODE || config.AUDIO_MODE === 'none') {
      // Silent preview / proxy-only test: captions are shown, no speech API is called.
      seconds = Math.max(11, Math.ceil(narration.split(/\s+/).length / 2.6) + 2);
    } else {
      const filename = path.join(folder, `scene-${index}.mp3`);
      const audio = config.AUDIO_MODE === 'proxy'
        ? await synthesizeProxySpeech(narration, filename)
        : await synthesizeSpeech(narration, filename);
      seconds = audio.durationSeconds + 0.8;
      audioUrl = `${config.PUBLIC_BASE_URL}/internal-assets/${job.jobId}/scene-${index}.mp3`;
    }
    scenes.push({
      type: storyScene.type, title: storyScene.title, narration,
      metrics: storyScene.factIds.map((id) => ({ label: facts[id]!.label, display: formatFact(facts[id]!) })),
      durationFrames: Math.ceil(seconds * config.VIDEO_FPS), audioUrl,
    });
    job.progress = 10 + Math.floor(((index + 1) / storyboard.scenes.length) * 48);
  }
  const frames = scenes.reduce((sum, scene) => sum + scene.durationFrames, 0);
  const totalSeconds = frames / config.VIDEO_FPS;
  if (totalSeconds > config.MAX_VIDEO_SECONDS) {
    throw new Error(`Narration duration ${Math.ceil(totalSeconds)}s exceeds the ${config.MAX_VIDEO_SECONDS}s limit. Shorten the storyboard and try again.`);
  }
  let musicUrl: string | null = null;
  if (!config.DEMO_MODE && config.GENERATE_MUSIC) {
    job.status = 'generating_music';
    try {
      const musicDestination = path.join(folder, 'music.mp3');
      if (config.MUSIC_FILE.trim()) {
        await copyFile(path.resolve(config.MUSIC_FILE), musicDestination);
      } else if (config.AUDIO_MODE === 'elevenlabs') {
        await synthesizeMusic(totalSeconds, musicDestination);
      } else {
        throw new Error('No music source configured.');
      }
      musicUrl = `${config.PUBLIC_BASE_URL}/internal-assets/${job.jobId}/music.mp3`;
    } catch {
      job.warnings.push('Music not available; continuing with narration only. Check MUSIC_FILE or ElevenLabs account.');
    }
  }
  job.status = 'rendering'; job.progress = 65;
  const outputFile = path.join(folder, 'video.mp4');
  const props: VideoProps = { scenes, musicUrl };
  await renderVideo(props, outputFile);
  job.outputFile = outputFile;
  job.status = 'completed'; job.progress = 100;
}
