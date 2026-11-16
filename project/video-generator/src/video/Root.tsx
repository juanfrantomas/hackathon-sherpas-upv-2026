import React from 'react';
import { Composition } from 'remotion';
import { FinancialVideo } from './compositions/FinancialVideo';
import type { VideoProps } from './types';

const defaultProps: VideoProps = {
  scenes: [{ type: 'intro', title: 'Your financial story', narration: 'A personalized financial story.', metrics: [], durationFrames: 150, audioUrl: null }],
  musicUrl: null,
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="FinancialStory"
    component={FinancialVideo}
    fps={30}
    width={1080}
    height={1920}
    durationInFrames={150}
    defaultProps={defaultProps}
    calculateMetadata={({ props }) => ({
      durationInFrames: props.scenes.reduce((sum, scene) => sum + scene.durationFrames, 0),
    })}
  />
);
