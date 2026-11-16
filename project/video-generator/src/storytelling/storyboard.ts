import { z } from 'zod';
import type { FactRegistry } from '../financial/factRegistry.js';
import { formatFact } from '../financial/factRegistry.js';

export const SceneSchema = z.object({
  type: z.enum(['intro', 'score', 'metric', 'priority', 'outro']),
  title: z.string().min(3).max(65),
  narrationTemplate: z.string().min(25).max(350),
  factIds: z.array(z.string()).max(2),
});
export const StoryboardSchema = z.object({ scenes: z.array(SceneSchema).min(5).max(8) });
export type Scene = z.infer<typeof SceneSchema>;
export type Storyboard = z.infer<typeof StoryboardSchema>;

const placeholders = /\{\{fact:([a-zA-Z0-9.]+)\}\}/g;
const digitPattern = /\d|[$€£]/;
const numberWordPattern = /\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|percent)\b/i;

export function validateStoryboard(output: unknown, registry: FactRegistry): Storyboard {
  const storyboard = StoryboardSchema.parse(output);
  let totalWords = 0;
  const referredTo = new Set<string>();
  for (const scene of storyboard.scenes) {
    if (digitPattern.test(scene.title) || numberWordPattern.test(scene.title)) {
      throw new Error(`Scene title contains an unverified numeric expression: ${scene.title}`);
    }
    const referencedIds = [...scene.narrationTemplate.matchAll(placeholders)].map((m) => m[1]!);
    const withoutFacts = scene.narrationTemplate.replace(placeholders, ' ');
    if (digitPattern.test(withoutFacts) || numberWordPattern.test(withoutFacts)) {
      throw new Error(`Scene '${scene.title}' contains numeric text outside fact references.`);
    }
    for (const id of [...scene.factIds, ...referencedIds]) {
      if (!registry[id]) throw new Error(`Unknown financial fact reference: ${id}`);
    }
    if (referencedIds.some((id) => !scene.factIds.includes(id))) {
      throw new Error(`Scene '${scene.title}' uses a fact not declared in factIds.`);
    }
    if (scene.factIds.some((id) => !referencedIds.includes(id))) {
      throw new Error(`Scene '${scene.title}' has an unused factId.`);
    }
    for (const id of referencedIds) referredTo.add(id);
    totalWords += renderNarration(scene, registry).split(/\s+/).length;
  }
  if (totalWords > 325) {
    throw new Error(`Narration too long (${totalWords} words); maximum 325 words for a 3-minute target.`);
  }
  if (referredTo.size < 5) throw new Error('Storyboard must include at least five distinct verified facts.');
  return storyboard;
}

export function renderNarration(scene: Scene, registry: FactRegistry): string {
  return scene.narrationTemplate.replace(placeholders, (_match, id: string) => {
    const fact = registry[id];
    if (!fact) throw new Error(`Unrecognized fact '${id}'.`);
    return formatFact(fact);
  });
}
