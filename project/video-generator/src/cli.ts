import { randomUUID } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { copyFile, mkdir, readFile, stat } from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import { config } from './config.js';
import { synthesizeMusic, synthesizeSpeech } from './audio/elevenlabs.js';
import { synthesizeProxySpeech } from './audio/proxyTts.js';
import { formatFact, createFactRegistry } from './financial/factRegistry.js';
import { generateStoryboard } from './storytelling/generate.js';
import { renderNarration } from './storytelling/storyboard.js';
import { validateDocuments } from './validation/documents.js';
import { renderVideo } from './video/render.js';
import type { RenderScene, VideoProps } from './video/types.js';

type CliArgs = {
  financialHealth: string;
  investmentAnalysis: string;
  persona: string;
  output: string;
  jobId: string;
};

function parseArgs(argv: string[]): CliArgs {
  const map = new Map<string, string>();
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    const val = argv[i + 1];
    if (key?.startsWith('--') && val !== undefined) {
      map.set(key.slice(2), val);
      i++;
    }
  }
  const financialHealth = map.get('financial-health');
  const investmentAnalysis = map.get('investment-analysis');
  const persona = map.get('persona');
  const output = map.get('output');
  if (!financialHealth || !investmentAnalysis || !persona || !output) {
    throw new Error('Usage: tsx src/cli.ts --financial-health <path> --investment-analysis <path> --persona <path> --output <path> [--job-id <id>]');
  }
  return {
    financialHealth,
    investmentAnalysis,
    persona,
    output,
    jobId: map.get('job-id') || randomUUID(),
  };
}

function emitProgress(payload: Record<string, unknown>): void {
  process.stdout.write(`PROGRESS:${JSON.stringify(payload)}\n`);
}

function startAssetServer(folder: string, jobId: string): Promise<{ port: number; close: () => Promise<void> }> {
  return new Promise((resolve, reject) => {
    const server = http.createServer(async (req, res) => {
      const urlPath = (req.url ?? '').split('?')[0] ?? '';
      const prefix = `/internal-assets/${jobId}/`;
      if (!urlPath.startsWith(prefix)) {
        res.statusCode = 404;
        res.end('Not found');
        return;
      }
      const filename = path.basename(urlPath.slice(prefix.length));
      if (!/^(?:scene-\d+|music)\.mp3$/.test(filename)) {
        res.statusCode = 404;
        res.end('Not found');
        return;
      }
      const fullPath = path.join(folder, filename);
      try {
        const info = await stat(fullPath);
        res.writeHead(200, {
          'Content-Type': 'audio/mpeg',
          'Content-Length': info.size,
        });
        createReadStream(fullPath).pipe(res);
      } catch {
        res.statusCode = 404;
        res.end('Asset not found');
      }
    });
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const addr = server.address();
      if (!addr || typeof addr === 'string') {
        reject(new Error('Failed to bind ephemeral asset server.'));
        return;
      }
      resolve({
        port: addr.port,
        close: () => new Promise<void>((res) => server.close(() => res())),
      });
    });
  });
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const folder = path.resolve('output', args.jobId);
  await mkdir(folder, { recursive: true });
  await mkdir(path.dirname(path.resolve(args.output)), { recursive: true });

  const warnings: string[] = [];
  const assetServer = await startAssetServer(folder, args.jobId);
  const assetBaseUrl = `http://127.0.0.1:${assetServer.port}`;

  try {
    emitProgress({ status: 'generating_storyboard', progress: 5 });
    const [fhRaw, iaRaw, personaRaw] = await Promise.all([
      readFile(args.financialHealth, 'utf8'),
      readFile(args.investmentAnalysis, 'utf8'),
      readFile(args.persona, 'utf8'),
    ]);

    const input = validateDocuments(JSON.parse(fhRaw), JSON.parse(iaRaw), personaRaw);
    const facts = createFactRegistry(input);
    const storyboard = await generateStoryboard(input, facts);

    emitProgress({ status: 'generating_audio', progress: 15 });
    const scenes: RenderScene[] = [];
    for (let index = 0; index < storyboard.scenes.length; index++) {
      const storyScene = storyboard.scenes[index]!;
      const narration = renderNarration(storyScene, facts);
      let seconds: number;
      let audioUrl: string | null = null;

      if (config.DEMO_MODE || config.AUDIO_MODE === 'none') {
        seconds = Math.max(11, Math.ceil(narration.split(/\s+/).length / 2.6) + 2);
      } else {
        const filename = path.join(folder, `scene-${index}.mp3`);
        const audio = config.AUDIO_MODE === 'proxy'
          ? await synthesizeProxySpeech(narration, filename)
          : await synthesizeSpeech(narration, filename);
        seconds = audio.durationSeconds + 0.8;
        audioUrl = `${assetBaseUrl}/internal-assets/${args.jobId}/scene-${index}.mp3`;
      }

      scenes.push({
        type: storyScene.type,
        title: storyScene.title,
        narration,
        metrics: storyScene.factIds.map((id) => ({
          label: facts[id]!.label,
          display: formatFact(facts[id]!),
        })),
        durationFrames: Math.ceil(seconds * config.VIDEO_FPS),
        audioUrl,
      });

      const pct = 15 + Math.floor(((index + 1) / storyboard.scenes.length) * 45);
      emitProgress({ status: 'generating_audio', progress: pct });
    }

    const frames = scenes.reduce((sum, scene) => sum + scene.durationFrames, 0);
    const totalSeconds = frames / config.VIDEO_FPS;
    if (totalSeconds > config.MAX_VIDEO_SECONDS) {
      throw new Error(`Narration duration ${Math.ceil(totalSeconds)}s exceeds ${config.MAX_VIDEO_SECONDS}s limit.`);
    }

    let musicUrl: string | null = null;
    if (!config.DEMO_MODE && config.GENERATE_MUSIC) {
      emitProgress({ status: 'generating_music', progress: 62 });
      try {
        const musicDestination = path.join(folder, 'music.mp3');
        if (config.MUSIC_FILE.trim()) {
          await copyFile(path.resolve(config.MUSIC_FILE), musicDestination);
        } else if (config.AUDIO_MODE === 'elevenlabs') {
          await synthesizeMusic(totalSeconds, musicDestination);
        } else {
          throw new Error('No music source configured.');
        }
        musicUrl = `${assetBaseUrl}/internal-assets/${args.jobId}/music.mp3`;
      } catch {
        warnings.push('Music not available; continuing with narration only.');
      }
    }

    emitProgress({ status: 'rendering', progress: 70 });
    const tempOutput = path.join(folder, 'video.mp4');
    const props: VideoProps = { scenes, musicUrl };
    await renderVideo(props, tempOutput);

    const finalOutput = path.resolve(args.output);
    await copyFile(tempOutput, finalOutput);

    emitProgress({
      status: 'completed',
      progress: 100,
      outputFile: finalOutput,
      warnings,
    });
  } finally {
    await assetServer.close();
  }
}

main().catch((err) => {
  const message = err instanceof Error ? err.message : String(err);
  process.stderr.write(`ERROR:${message}\n`);
  process.exit(1);
});
