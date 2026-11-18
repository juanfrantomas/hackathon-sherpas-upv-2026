/**
 * Records an interactive ~2-minute MP4 demo video of the live MySherpas frontend
 * using Chrome DevTools Protocol (cdp.mjs) + AI voiceovers (output/audio/*.mp3).
 *
 * Usage:
 *   node record_interactive.mjs [http://localhost:5173]
 */
import { execFileSync, spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCENES_PATH = path.join(__dirname, 'scenes.json');
const OUTPUT_DIR = path.join(__dirname, 'output');
const AUDIO_DIR = path.join(OUTPUT_DIR, 'audio');
const FRAMES_DIR = path.join(OUTPUT_DIR, 'frames');
const CLIPS_DIR = path.join(OUTPUT_DIR, 'clips_interactive');
const FINAL_VIDEO = path.join(OUTPUT_DIR, 'demo-interactive-2min.mp4');

const REMOTION_BIN_DIR = path.resolve(
  __dirname,
  '../video-generator/node_modules/@remotion/compositor-win32-x64-msvc',
);

function resolveBinary(name) {
  const exe = process.platform === 'win32' ? `${name}.exe` : name;
  const bundled = path.join(REMOTION_BIN_DIR, exe);
  return fs.existsSync(bundled) ? bundled : exe;
}

const FFMPEG = resolveBinary('ffmpeg');
const FFPROBE = resolveBinary('ffprobe');

function resolveBrowserPath() {
  if (process.env.CHROME_PATH && fs.existsSync(process.env.CHROME_PATH)) {
    return process.env.CHROME_PATH;
  }
  const localAppData = process.env.LOCALAPPDATA ?? '';
  const candidates = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    path.join(localAppData, 'Google/Chrome/Application/chrome.exe'),
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  ];
  return candidates.find((p) => p && fs.existsSync(p)) ?? null;
}

function getAudioDuration(mp3Path) {
  try {
    const out = execFileSync(
      FFPROBE,
      [
        '-v',
        'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=noprint_wrappers=1:nokey=1',
        mp3Path,
      ],
      { encoding: 'utf8' },
    ).trim();
    const val = Number.parseFloat(out);
    if (Number.isFinite(val) && val > 0) return val;
  } catch {
    /* fallback below */
  }
  const bytes = fs.statSync(mp3Path).size;
  return Math.max(3.0, (bytes * 8) / 48000);
}

async function isServerUp(url) {
  try {
    const res = await fetch(url);
    return res.ok;
  } catch {
    return false;
  }
}

async function ensureFrontendServer(url) {
  if (await isServerUp(url)) {
    console.log(`Frontend ya activo en ${url}`);
    return null;
  }
  console.log('Iniciando frontend (pnpm dev)...');
  const frontendDir = path.resolve(__dirname, '../frontend');
  const child = spawn('pnpm', ['dev', '--port', '5173'], {
    cwd: frontendDir,
    shell: true,
    stdio: 'ignore',
  });
  for (let i = 0; i < 40; i += 1) {
    if (await isServerUp(url)) {
      console.log(`Frontend listo en ${url}`);
      return child;
    }
    await sleep(500);
  }
  child.kill();
  throw new Error(`No se pudo iniciar el frontend en ${url}`);
}

async function injectDemoOverlay(page) {
  await page.evaluate(`(() => {
    if (document.getElementById('__demo-cursor')) return;
    const style = document.createElement('style');
    style.textContent = \`
      #__demo-cursor {
        position: fixed;
        top: 0; left: 0;
        width: 22px; height: 22px;
        border-radius: 50%;
        background: rgba(56, 189, 248, 0.9);
        border: 3px solid #ffffff;
        box-shadow: 0 4px 14px rgba(0,0,0,0.45);
        pointer-events: none;
        z-index: 2147483647;
        transform: translate(720px, 450px);
        transition: transform 0.45s cubic-bezier(0.22, 1, 0.36, 1);
      }
      #__demo-cursor.clicking::after {
        content: '';
        position: absolute;
        inset: -10px;
        border-radius: 50%;
        border: 3px solid #38bdf8;
        opacity: 0.9;
      }
      #__demo-banner {
        position: fixed;
        left: 24px;
        bottom: 20px;
        max-width: 520px;
        background: rgba(11, 18, 32, 0.92);
        border: 1px solid rgba(56, 189, 248, 0.65);
        border-left: 5px solid #38bdf8;
        border-radius: 12px;
        padding: 14px 20px;
        color: #f8fafc;
        font-family: 'Segoe UI', system-ui, sans-serif;
        box-shadow: 0 12px 30px rgba(0,0,0,0.45);
        z-index: 2147483646;
        pointer-events: none;
      }
      #__demo-banner h3 {
        margin: 0 0 4px 0;
        font-size: 18px;
        font-weight: 700;
        color: #ffffff;
      }
      #__demo-banner p {
        margin: 0;
        font-size: 13px;
        color: #cbd5e1;
        line-height: 1.35;
      }
    \`;
    document.head.appendChild(style);

    const cursor = document.createElement('div');
    cursor.id = '__demo-cursor';
    document.body.appendChild(cursor);

    const banner = document.createElement('div');
    banner.id = '__demo-banner';
    banner.innerHTML = '<h3></h3><p></p>';
    document.body.appendChild(banner);
  })()`);
}

async function setBanner(page, title, subtitle) {
  await page.evaluate(`(() => {
    const b = document.getElementById('__demo-banner');
    if (!b) return;
    b.querySelector('h3').textContent = ${JSON.stringify(title)};
    b.querySelector('p').textContent = ${JSON.stringify(subtitle)};
  })()`);
}

async function moveAndClick(page, selector, matchText = null) {
  const clicked = await page.evaluate(`(() => {
    const nodes = [...document.querySelectorAll(${JSON.stringify(selector)})];
    const el = ${matchText === null ? 'nodes[0]' : `nodes.find((n) => n.textContent.trim().includes(${JSON.stringify(matchText)}))`};
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const x = Math.round(rect.left + rect.width / 2);
    const y = Math.round(rect.top + rect.height / 2);
    const c = document.getElementById('__demo-cursor');
    if (c) {
      c.style.transform = \`translate(\${x - 11}px, \${y - 11}px)\`;
    }
    window.__pendingClickEl = el;
    return true;
  })()`);
  if (!clicked) return false;
  await sleep(500);
  await page.evaluate(`(() => {
    const c = document.getElementById('__demo-cursor');
    if (c) c.classList.add('clicking');
    if (window.__pendingClickEl) window.__pendingClickEl.click();
  })()`);
  await sleep(220);
  await page.evaluate(`(() => {
    const c = document.getElementById('__demo-cursor');
    if (c) c.classList.remove('clicking');
  })()`);
  return true;
}

async function scrollPhone(page, topPx) {
  await page.evaluate(`(() => {
    const scroller =
      document.querySelector('.phone__screen') ||
      document.querySelector('.screen') ||
      document.querySelector('.phone');
    if (scroller) scroller.scrollTo({ top: ${topPx}, behavior: 'smooth' });
  })()`);
}

async function runSceneActions(page, sceneId) {
  switch (sceneId) {
    case '01-hook':
      await moveAndClick(page, '.proto-bar .seg button', 'Family app');
      await sleep(1800);
      await scrollPhone(page, 220);
      await sleep(1800);
      await scrollPhone(page, 0);
      break;

    case '02-welcome':
      await moveAndClick(page, '.household-btn', 'Weah');
      await sleep(2200);
      await moveAndClick(page, '.household-btn', 'Carter');
      break;

    case '03-story':
      await moveAndClick(page, '.flow ol li button', 'Financial story');
      await sleep(2000);
      await moveAndClick(page, '.player__progress .seg-bar:nth-child(2)');
      await sleep(2500);
      await moveAndClick(page, '.player__progress .seg-bar:nth-child(3)');
      break;

    case '04-dashboard':
      await moveAndClick(page, '.flow ol li button', 'Home dashboard');
      await sleep(2000);
      await scrollPhone(page, 320);
      await sleep(2400);
      await scrollPhone(page, 0);
      break;

    case '05-plan':
      await moveAndClick(page, '.flow ol li button', 'My financial plan');
      await sleep(1800);
      await scrollPhone(page, 360);
      await sleep(2200);
      await scrollPhone(page, 0);
      break;

    case '06-milestones':
      await moveAndClick(page, '.flow ol li button', 'Goals & milestones');
      await sleep(2500);
      await scrollPhone(page, 260);
      await sleep(2000);
      await moveAndClick(page, '.flow ol li button', 'Progress overview');
      break;

    case '07-checkin':
      await moveAndClick(page, '.flow ol li button', 'Check-in');
      await sleep(2000);
      await scrollPhone(page, 240);
      await sleep(2000);
      await scrollPhone(page, 0);
      break;

    case '08-mentor':
      await moveAndClick(page, '.flow ol li button', 'AI mentor');
      await sleep(1400);
      await moveAndClick(page, '.state-grid button', 'Listening');
      await sleep(1800);
      await moveAndClick(page, '.state-grid button', 'Thinking');
      await sleep(1800);
      await moveAndClick(page, '.state-grid button', 'Speaking');
      break;

    case '09-video-ia':
      await moveAndClick(page, '.flow ol li button', 'Progress overview');
      await sleep(2000);
      await scrollPhone(page, 300);
      break;

    default:
      break;
  }
}

async function encodeSceneFrames(ffmpegPath, frames, fallbackBuf, durSeconds, audioPath, clipOut) {
  const fps = 30;
  const totalFrames = Math.max(1, Math.round(durSeconds * fps));

  const proc = spawn(
    ffmpegPath,
    [
      '-y',
      '-f',
      'image2pipe',
      '-vcodec',
      'mjpeg',
      '-framerate',
      String(fps),
      '-i',
      '-',
      '-i',
      audioPath,
      '-t',
      String(durSeconds),
      '-c:v',
      'libx264',
      '-preset',
      'fast',
      '-pix_fmt',
      'yuv420p',
      '-c:a',
      'aac',
      '-b:a',
      '192k',
      '-ar',
      '44100',
      '-ac',
      '2',
      clipOut,
    ],
    { stdio: ['pipe', 'ignore', 'pipe'] },
  );

  let stderr = '';
  proc.stderr.on('data', (chunk) => {
    stderr += chunk.toString();
  });

  const done = new Promise((resolve, reject) => {
    proc.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`FFmpeg exited with code ${code}: ${stderr.slice(-500)}`));
    });
    proc.on('error', reject);
  });

  let idx = 0;
  let currentBuf = fallbackBuf;

  for (let f = 0; f < totalFrames; f += 1) {
    const tMs = (f / fps) * 1000;
    while (idx < frames.length && frames[idx].t <= tMs) {
      currentBuf = frames[idx].buf;
      idx += 1;
    }
    if (!proc.stdin.write(currentBuf)) {
      await new Promise((res) => proc.stdin.once('drain', res));
    }
  }
  proc.stdin.end();
  await done;
}

async function main() {
  const url = process.argv[2] ?? 'http://localhost:5173';
  const browserPath = resolveBrowserPath();
  if (!browserPath) {
    throw new Error('No se encontró Chrome ni Edge. Define CHROME_PATH.');
  }

  // Ensure cdp.mjs finds Chrome/Edge on Windows before importing it
  process.env.CHROME_PATH = browserPath;
  const { launch } = await import('../frontend/scripts/cdp.mjs');

  fs.mkdirSync(CLIPS_DIR, { recursive: true });

  const config = JSON.parse(fs.readFileSync(SCENES_PATH, 'utf8'));
  const serverProc = await ensureFrontendServer(url);
  const page = await launch({ port: 9334, width: 1440, height: 900 });

  try {
    await page.goto(url);
    await sleep(800);
    await injectDemoOverlay(page);

    const clipPaths = [];
    let totalSeconds = 0;

    for (let i = 0; i < config.scenes.length; i += 1) {
      const scene = config.scenes[i];
      const audioPath = path.join(AUDIO_DIR, `${scene.id}.mp3`);
      if (!fs.existsSync(audioPath)) {
        throw new Error(`Falta el audio ${audioPath}. Ejecuta generate_tts.py primero.`);
      }

      const dur = Number((getAudioDuration(audioPath) + 0.5).toFixed(2));
      totalSeconds += dur;

      await setBanner(page, scene.title, scene.subtitle);
      await sleep(80);

      console.log(`[${i + 1}/${config.scenes.length}] Grabando 30fps: ${scene.id} (${dur.toFixed(1)}s)...`);

      const initShot = await page.send('Page.captureScreenshot', {
        format: 'jpeg',
        quality: 90,
      });
      const fallbackBuf = Buffer.from(initShot.data, 'base64');

      const frames = [];
      const startTime = Date.now();

      const stopListening = page.on('Page.screencastFrame', ({ data, sessionId }) => {
        frames.push({ t: Date.now() - startTime, buf: Buffer.from(data, 'base64') });
        page.send('Page.screencastFrameAck', { sessionId }).catch(() => {});
      });

      await page.send('Page.startScreencast', {
        format: 'jpeg',
        quality: 90,
        everyNthFrame: 1,
      });

      await runSceneActions(page, scene.id);
      const elapsedMs = Date.now() - startTime;
      const remainingMs = Math.max(0, dur * 1000 - elapsedMs);
      if (remainingMs > 0) await sleep(remainingMs);

      await page.send('Page.stopScreencast');
      stopListening();

      const clipOut = path.join(CLIPS_DIR, `${scene.id}.mp4`);
      clipPaths.push(clipOut);

      await encodeSceneFrames(FFMPEG, frames, fallbackBuf, dur, audioPath, clipOut);
      console.log(`  -> ${frames.length} frames capturados -> 30 fps -> ${scene.id}.mp4`);
    }

    const concatTxt = path.join(OUTPUT_DIR, 'concat_interactive.txt');
    fs.writeFileSync(
      concatTxt,
      clipPaths.map((p) => `file '${p.replace(/\\/g, '/')}'`).join('\n'),
      'utf8',
    );

    execFileSync(
      FFMPEG,
      [
        '-y',
        '-f',
        'concat',
        '-safe',
        '0',
        '-i',
        concatTxt,
        '-c',
        'copy',
        '-movflags',
        '+faststart',
        FINAL_VIDEO,
      ],
      { stdio: 'pipe' },
    );

    const mins = Math.floor(totalSeconds / 60);
    const secs = Math.round(totalSeconds % 60)
      .toString()
      .padStart(2, '0');
    console.log(`\n¡LISTO! Video interactivo generado en:\n${FINAL_VIDEO}`);
    console.log(`Duración total: ${mins}:${secs} (${totalSeconds.toFixed(1)}s)`);
  } finally {
    page.close();
    if (serverProc) serverProc.kill();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
