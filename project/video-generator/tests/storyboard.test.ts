import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { validateDocuments } from '../src/validation/documents.js';
import { createFactRegistry } from '../src/financial/factRegistry.js';
import { validateStoryboard, renderNarration, type Scene } from '../src/storytelling/storyboard.js';
import { parsePersona } from '../src/storytelling/persona.js';

const file = (name: string) => readFileSync(path.resolve('examples', name), 'utf8');
const input = validateDocuments(JSON.parse(file('financial-health.json')), JSON.parse(file('investment-analysis.json')), file('persona.md'));
const facts = createFactRegistry(input);
const validScene = (id: string): Scene => ({
  type: 'metric', title: 'Understanding the report',
  narrationTemplate: `Your financial report identifies {{fact:${id}}}. This figure comes from the verified report data, not a new estimate.`,
  factIds: [id],
});

describe('storyboard safety contract', () => {
  it('replaces fact placeholders using registry values', () => {
    expect(renderNarration(validScene('cash.accessible'), facts)).toContain('$19,000');
  });
  it('rejects invented numeric claims', () => {
    const scenes = ['health.score', 'cash.accessible', 'education.fundingGap', 'retirement.fundingGap', 'household.netWorth'].map(validScene);
    scenes[0]!.narrationTemplate += ' You will earn 9999 dollars.';
    expect(() => validateStoryboard({ scenes }, facts)).toThrow(/numeric text/);
  });
  it('rejects references to unavailable facts', () => {
    const scenes = ['health.score', 'cash.accessible', 'education.fundingGap', 'retirement.fundingGap', 'missing.fact'].map(validScene);
    expect(() => validateStoryboard({ scenes }, facts)).toThrow(/Unknown financial fact/);
  });
  it('keeps the motivation confidence qualifier', () => {
    const persona = parsePersona(input.personaMarkdown);
    expect(persona.motivationalAnchor).toBe('PROTECTION');
    expect(persona.motivationConfidence).toBe('low');
  });
});
