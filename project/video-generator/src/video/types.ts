export type RenderScene = {
  type: 'intro' | 'score' | 'metric' | 'priority' | 'outro';
  title: string;
  narration: string;
  metrics: Array<{ label: string; display: string }>;
  durationFrames: number;
  audioUrl: string | null;
};

export type VideoProps = {
  scenes: RenderScene[];
  musicUrl: string | null;
};
