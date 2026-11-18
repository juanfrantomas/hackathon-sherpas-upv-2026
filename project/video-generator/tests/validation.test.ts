import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { validateDocuments } from '../src/validation/documents.js';

const fixture = (name: string) => readFileSync(path.resolve('examples', name), 'utf8');
const financialHealth = JSON.parse(fixture('financial-health.json'));
const investmentAnalysis = JSON.parse(fixture('investment-analysis.json'));
const persona = fixture('persona.md');

describe('input data contract', () => {
  it('accepts the supplied example files', () => {
    const input = validateDocuments(financialHealth, investmentAnalysis, persona);
    expect(input.financialHealth.score.published_score).toBe(52);
    expect(input.financialHealth.case.slug).toBe('daniel-emily-johnson');
  });

  it('rejects unsupported schema version', () => {
    const modified = structuredClone(financialHealth);
    modified.schema_version = 999;
    expect(() => validateDocuments(modified, investmentAnalysis, persona)).toThrow();
  });

  it('rejects different households', () => {
    const modified = structuredClone(investmentAnalysis);
    modified.case.slug = 'different-household';
    expect(() => validateDocuments(financialHealth, modified, persona)).toThrow(/same case/);
  });

  it('rejects incorrect score type', () => {
    const modified = structuredClone(financialHealth);
    modified.score.published_score = 'fifty-two';
    expect(() => validateDocuments(modified, investmentAnalysis, persona)).toThrow();
  });
});
