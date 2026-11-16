import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { validateDocuments } from '../src/validation/documents.js';
import { createFactRegistry, formatFact } from '../src/financial/factRegistry.js';

const fixture = (name: string) => readFileSync(path.resolve('examples', name), 'utf8');
const financialHealth = JSON.parse(fixture('financial-health.json'));
const investmentAnalysis = JSON.parse(fixture('investment-analysis.json'));
const persona = fixture('persona.md');

const build = (fh: unknown = financialHealth, ia: unknown = investmentAnalysis) =>
  createFactRegistry(validateDocuments(fh, ia, persona));

describe('financial fact registry', () => {
  it('extracts exact values with their correct meaning', () => {
    const facts = build();
    expect(facts['health.score']?.rawValue).toBe(52);
    expect(facts['cash.accessible']?.rawValue).toBe(19000);
    expect(facts['cash.totalCashTargetMin']?.rawValue).toBe(111360);
    expect(facts['cash.emergencyReserveMin']?.rawValue).toBe(106860);
    expect(facts['retirement.fundingGap']?.rawValue).toBe(1427455.89);
    expect(facts['debt.cardAPR']?.rawValue).toBeCloseTo(24.9);
    expect(facts['retirement.savingsCapacity']?.rawValue).toBe(15032.01);
    expect(formatFact(facts['retirement.savingsCapacity']!)).toBe('$15,032 per year');
  });

  it('rejects a changed authoritative value in investment-analysis', () => {
    const modified = structuredClone(investmentAnalysis);
    modified.key_metrics.facts.cash.accessibleCash.value = 500000;
    expect(() => build(financialHealth, modified)).toThrow(/Conflicting authoritative fact/);
  });

  it('rejects a conflicting duplicate retirement figure', () => {
    const modified = structuredClone(investmentAnalysis);
    modified.key_metrics.capacity.retirementGap = 123;
    expect(() => build(financialHealth, modified)).toThrow(/Conflicting report values/);
  });
});
