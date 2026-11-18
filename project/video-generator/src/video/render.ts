import path from 'node:path';
import { bundle } from '@remotion/bundler';
import { selectComposition, renderMedia } from '@remotion/renderer';
import type { VideoProps } from './types.js';

let bundled: Promise<string> | null = null;
function getBundle(): Promise<string> {
  // Build the Remotion bundle once per server process, reuse for every job.
  return bundled ?? (bundled = bundle({ entryPoint: path.resolve(process.cwd(), 'src/video/index.ts') }));
}

export async function renderVideo(props: VideoProps, outputFile: string): Promise<void> {
  const serveUrl = await getBundle();
  const composition = await selectComposition({ serveUrl, id: 'FinancialStory', inputProps: props });
  await renderMedia({
    serveUrl, composition, inputProps: props,
    codec: 'h264', audioCodec: 'aac',
    outputLocation: outputFile,
    concurrency: 1,
  });
}
