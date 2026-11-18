import React from 'react';
import { AbsoluteFill, Audio, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { RenderScene } from '../types';

const colors = {
  ink: '#EAF2FF',
  muted: '#A5B5D0',
  blue: '#70C9EF',
  green: '#9DE0C3',
};

type Props = { scene: RenderScene; sceneIndex: number; totalScenes: number };

// Short caption chunks read well on small phone screens. This is a proportional
// approximation, not word-level synchronization. Exact TTS timings are a V2 goal.
function splitCaptions(text: string): string[] {
  const words = text.trim().split(/\s+/);
  const chunks: string[] = [];
  let current = '';
  for (const word of words) {
    if (current.length + word.length + 1 > 74 && current) {
      chunks.push(current);
      current = '';
    }
    current += current ? ` ${word}` : word;
  }
  if (current) chunks.push(current);
  return chunks.length ? chunks : [''];
}

export const StoryScene: React.FC<Props> = ({ scene, sceneIndex, totalScenes }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrance = spring({ frame, fps, config: { damping: 18, stiffness: 85 } });
  const fadeOut = interpolate(frame, [scene.durationFrames - 15, scene.durationFrames], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const captions = splitCaptions(scene.narration);
  const captionIndex = Math.min(captions.length - 1, Math.floor((frame / scene.durationFrames) * captions.length));
  const topLabel = scene.type === 'intro' ? 'YOUR FINANCIAL STORY' : 'FINANCIAL REPORT EXPLAINED';

  return (
    <AbsoluteFill style={{
      background: 'radial-gradient(circle at 10% 18%, #163654 0%, #0E1D34 43%, #091321 100%)',
      fontFamily: 'Arial, Helvetica, sans-serif',
      color: colors.ink,
      opacity: fadeOut,
      overflow: 'hidden',
    }}>
      <div style={{ position: 'absolute', top: -200, right: -240, width: 760, height: 760, borderRadius: '50%', background: 'rgba(63,166,213,.075)' }} />
      <div style={{ position: 'absolute', bottom: -270, left: -300, width: 820, height: 820, borderRadius: '50%', background: 'rgba(62,160,127,.055)' }} />
      <div style={{ position: 'absolute', top: 180, left: 74, right: 74, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 28, color: colors.blue, fontWeight: 800, letterSpacing: 5 }}>{topLabel}</div>
        <div style={{ fontSize: 28, color: colors.muted }}>{String(sceneIndex + 1).padStart(2, '0')} / {String(totalScenes).padStart(2, '0')}</div>
      </div>
      <div style={{ position: 'absolute', top: 310, left: 74, right: 74, transform: `translateY(${(1 - entrance) * 55}px)`, opacity: entrance }}>
        <div style={{ height: 7, width: 110, borderRadius: 99, background: colors.green, marginBottom: 42 }} />
        <div style={{ fontSize: 78, fontWeight: 800, letterSpacing: -1, lineHeight: 1.1, overflowWrap: 'break-word' }}>
          {scene.title}
        </div>
      </div>
      <div style={{ position: 'absolute', top: 685, left: 74, right: 74, display: 'flex', flexDirection: 'column', gap: 30 }}>
        {scene.metrics.slice(0, 2).map((metric, index) => (
          <div key={metric.label} style={{
            padding: '42px 46px', background: 'rgba(255,255,255,.065)', border: '1px solid rgba(157,224,195,.23)',
            borderRadius: 28,
            opacity: interpolate(frame, [12 + index * 8, 30 + index * 8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          }}>
            <div style={{ color: colors.muted, fontSize: 34, lineHeight: 1.23, marginBottom: 18 }}>{metric.label}</div>
            <div style={{ color: colors.green, fontSize: metric.display.length > 18 ? 56 : 73, fontWeight: 800, letterSpacing: -2, overflowWrap: 'break-word' }}>{metric.display}</div>
          </div>
        ))}
      </div>
      <div style={{ position: 'absolute', bottom: 190, left: 74, right: 74, borderTop: '1px solid rgba(255,255,255,.15)', paddingTop: 35 }}>
        <div style={{ fontSize: 37, lineHeight: 1.37, color: colors.ink }}>
          {captions[captionIndex]}
        </div>
      </div>
      <div style={{ position: 'absolute', bottom: 115, left: 74, right: 74, height: 8, borderRadius: 20, background: 'rgba(255,255,255,.12)' }}>
        <div style={{ height: '100%', width: `${Math.min(100, ((sceneIndex + frame / scene.durationFrames) / totalScenes) * 100)}%`, background: colors.blue, borderRadius: 20 }} />
      </div>
      {scene.audioUrl && <Audio src={scene.audioUrl} />}
    </AbsoluteFill>
  );
};
