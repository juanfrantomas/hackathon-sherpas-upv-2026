/**
 * Generates a ~2-minute MP4 demo video showcasing MySherpas features with AI voiceover.
 *
 * Usage:
 *   node build_demo_video.mjs [--capture http://localhost:5173] [--force-tts]
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCENES_PATH = path.join(__dirname, 'scenes.json');
const OUTPUT_DIR = path.join(__dirname, 'output');
const SHOTS_DIR = path.join(OUTPUT_DIR, 'shots');
const AUDIO_DIR = path.join(OUTPUT_DIR, 'audio');
const CLIPS_DIR = path.join(OUTPUT_DIR, 'clips');
const FINAL_VIDEO = path.join(OUTPUT_DIR, 'demo-features-2min.mp4');

const REMOTION_BIN_DIR = path.resolve(
  __dirname,
  '../video-generator/node_modules/@remotion/compositor-win32-x64-msvc',
);

function resolveBinary(name) {
  const exe = process.platform === 'win32' ? `${name}.exe` : name;
  const bundled = path.join(REMOTION_BIN_DIR, exe);
  if (fs.existsSync(bundled)) return bundled;
  return exe;
}

const FFMPEG = resolveBinary('ffmpeg');
const FFPROBE = resolveBinary('ffprobe');

function resolveFontOption() {
  const candidates = [
    'C:/Windows/Fonts/segoeuib.ttf',
    'C:/Windows/Fonts/segoeui.ttf',
    'C:/Windows/Fonts/arial.ttf',
  ];
  const found = candidates.find((p) => fs.existsSync(p));
  if (!found) return '';
  // In FFmpeg filter_complex on Windows: backslashes and drive colons must be escaped
  const escaped = found.replace(/\\/g, '/').replace(':', '\\:');
  return `fontfile='${escaped}':`;
}

function escapeDrawtext(text) {
  return String(text)
    .replace(/\\/g, '\\\\')
    .replace(/:/g, '\\:')
    .replace(/'/g, '') // remove single quotes to avoid breaking FFmpeg parser
    .replace(/,/g, '\\,')
    .replace(/%/g, '\\%');
}

function getAudioDuration(mp3Path) {
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
  const seconds = Number.parseFloat(out);
  if (!Number.isFinite(seconds) || seconds <= 0) {
    throw new Error(`Invalid audio duration for ${mp3Path}: "${out}"`);
  }
  return seconds;
}

function parseArgs(argv) {
  let captureUrl = null;
  let forceTts = false;
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--capture' && argv[i + 1]) {
      captureUrl = argv[i + 1];
      i += 1;
    } else if (argv[i] === '--force-tts') {
      forceTts = true;
    }
  }
  return { captureUrl, forceTts };
}

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

function main() {
  const { captureUrl, forceTts } = parseArgs(process.argv.slice(2));
  const config = JSON.parse(fs.readFileSync(SCENES_PATH, 'utf8'));
  const fps = config.fps ?? 30;
  const width = config.width ?? 1920;
  const height = config.height ?? 1080;

  fs.mkdirSync(SHOTS_DIR, { recursive: true });
  fs.mkdirSync(AUDIO_DIR, { recursive: true });
  fs.mkdirSync(CLIPS_DIR, { recursive: true });

  // 1. Optional: capture live screenshots from running frontend
  if (captureUrl) {
    const captureScript = path.resolve(__dirname, '../frontend/scripts/capture.mjs');
    const browserPath = resolveBrowserPath();
    if (!browserPath) {
      throw new Error(
        'No se encontró Chrome ni Edge. Define la variable CHROME_PATH con la ruta a chrome.exe o msedge.exe.',
      );
    }
    console.log(`\n[1/4] Capturando pantallas desde ${captureUrl} (usando ${browserPath})...`);
    execFileSync('node', [captureScript, captureUrl, SHOTS_DIR, 'demo'], {
      stdio: 'inherit',
      env: { ...process.env, CHROME_PATH: browserPath },
    });
  } else {
    console.log(`\n[1/4] Usando capturas existentes en ${SHOTS_DIR} (pasa --capture <url> para refrescarlas).`);
  }

  // 2. Generate AI voiceovers
  console.log('\n[2/4] Generando locución con IA...');
  const ttsArgs = [path.join(__dirname, 'generate_tts.py')];
  if (forceTts) ttsArgs.push('--force');
  execFileSync('python', ttsArgs, { stdio: 'inherit' });

  // 3. Render each scene clip
  console.log('\n[3/4] Renderizando escenas con FFmpeg...');
  const clipPaths = [];
  let totalSeconds = 0;

  for (const scene of config.scenes) {
    const audioPath = path.join(AUDIO_DIR, `${scene.id}.mp3`);
    const audioDuration = getAudioDuration(audioPath);
    const clipDuration = Number((audioDuration + 0.6).toFixed(2));
    totalSeconds += clipDuration;

    const clipPath = path.join(CLIPS_DIR, `${scene.id}.mp4`);
    clipPaths.push(clipPath);

    const titleFile = path.join(CLIPS_DIR, `${scene.id}_title.txt`);
    const subtitleFile = path.join(CLIPS_DIR, `${scene.id}_sub.txt`);
    fs.writeFileSync(titleFile, scene.title, 'utf8');
    fs.writeFileSync(subtitleFile, scene.subtitle, 'utf8');

    const tfEscaped = titleFile.replace(/\\/g, '/').replace(':', '\\:');
    const sfEscaped = subtitleFile.replace(/\\/g, '/').replace(':', '\\:');

    const overlayFilter = [
      `drawbox=x=0:y=${height - 170}:w=${width}:h=170:color=0x0b1220@0.92:t=fill`,
      `drawbox=x=0:y=${height - 170}:w=${width}:h=3:color=0x38bdf8@0.9:t=fill`,
      `drawtext=${fontOpt}textfile='${tfEscaped}':fontcolor=white:fontsize=40:x=72:y=${height - 138}`,
      `drawtext=${fontOpt}textfile='${sfEscaped}':fontcolor=0xcbd5e1:fontsize=26:x=72:y=${height - 76}`,
    ].join(',');

    const videoFile = scene.video ? path.resolve(__dirname, scene.video) : null;
    const imageFile = scene.image ? path.join(SHOTS_DIR, scene.image) : null;

    const args = ['-y'];
    let filterComplex;

    if (videoFile && fs.existsSync(videoFile)) {
      args.push('-stream_loop', '-1', '-i', videoFile, '-i', audioPath);
      filterComplex = `[0:v]scale=${width}:${height - 180}:force_original_aspect_ratio=decrease,pad=w=${width}:h=${height}:x=(ow-iw)/2:y=20:color=0x0f172a,setsar=1,fps=${fps},${overlayFilter}[v]`;
    } else if (imageFile && fs.existsSync(imageFile)) {
      args.push('-loop', '1', '-i', imageFile, '-i', audioPath);
      filterComplex = `[0:v]scale=${width}:${height - 180}:force_original_aspect_ratio=decrease,pad=w=${width}:h=${height}:x=(ow-iw)/2:y=20:color=0x0f172a,setsar=1,fps=${fps},${overlayFilter}[v]`;
    } else {
      console.warn(`  ! Sin captura para ${scene.id} (${scene.image ?? 'none'}); usando tarjeta de título.`);
      args.push('-f', 'lavfi', '-i', `color=c=0x0f172a:s=${width}x${height}:r=${fps}`, '-i', audioPath);
      filterComplex = `[0:v]${overlayFilter}[v]`;
    }

    args.push(
      '-filter_complex',
      filterComplex,
      '-map',
      '[v]',
      '-map',
      '1:a',
      '-t',
      String(clipDuration),
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
      clipPath,
    );

    execFileSync(FFMPEG, args, { stdio: 'pipe' });
    console.log(`  [clip] ${scene.id}.mp4 (${clipDuration.toFixed(1)}s)`);
  }

  // 4. Concatenate all clips into final MP4
  console.log('\n[4/4] Uniendo escenas en el MP4 final...');
  const concatFile = path.join(OUTPUT_DIR, 'concat.txt');
  const concatContent = clipPaths
    .map((p) => `file '${p.replace(/\\/g, '/').replace(/'/g, "'\\''")}'`)
    .join('\n');
  fs.writeFileSync(concatFile, concatContent, 'utf8');

  execFileSync(
    FFMPEG,
    ['-y', '-f', 'concat', '-safe', '0', '-i', concatFile, '-c', 'copy', '-movflags', '+faststart', FINAL_VIDEO],
    { stdio: 'pipe' },
  );

  const mins = Math.floor(totalSeconds / 60);
  const secs = Math.round(totalSeconds % 60)
    .toString()
    .padStart(2, '0');
  console.log(`\nListo! Video generado en:\n  ${FINAL_VIDEO}`);
  console.log(`Duración total aproximada: ${mins}:${secs} (${totalSeconds.toFixed(1)}s)`);
}

main();
