import React from 'react';
import { AbsoluteFill, Audio, Sequence, useCurrentFrame } from 'remotion';
import { StoryScene } from '../components/StoryScene';
import type { VideoProps } from '../types';

export const FinancialVideo: React.FC<VideoProps> = ({ scenes, musicUrl }) => {
  let offset = 0;
  const frame = useCurrentFrame();
  const totalFrames = scenes.reduce((sum, scene) => sum + scene.durationFrames, 0);
  const musicFadeIn = Math.min(1, frame / 30);
  const musicFadeOut = Math.max(0, Math.min(1, (totalFrames - frame) / 90));
  return (
    <AbsoluteFill>
      {scenes.map((scene, index) => {
        const from = offset;
        offset += scene.durationFrames;
        return (
          <Sequence key={`${index}-${scene.title}`} from={from} durationInFrames={scene.durationFrames}>
            <StoryScene scene={scene} sceneIndex={index} totalScenes={scenes.length} />
          </Sequence>
        );
      })}
      {musicUrl && <Audio src={musicUrl} volume={0.08 * Math.min(musicFadeIn, musicFadeOut)} loop />}
    </AbsoluteFill>
  );
};
