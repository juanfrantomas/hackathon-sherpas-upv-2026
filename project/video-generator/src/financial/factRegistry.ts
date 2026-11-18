import type { ValidatedInput } from '../validation/documents.js';

export type FactUnit = 'USD' | 'USD/yr' | 'percent' | 'months' | 'score';

export type FinancialFact = {
  id: string;
  label: string;
  rawValue: number; // Value in the source's native unit; percent values normalized to 0-100.
  unit: FactUnit;
  source: 'financial-health' | 'investment-analysis';
  sourcePath: string;
  guidance: string;
};

export type FactRegistry = Record<string, FinancialFact>;

function getPath(object: unknown, path: string): unknown {
  return path.split('.').reduce<unknown>((current, key) => {
    if (typeof current !== 'object' || current === null) return undefined;
    return (current as Record<string, unknown>)[key];
  }, object);
}

function asNumber(value: unknown, context: string): number {
  const converted = typeof value === 'string'
    ? Number(value.trim().replace(/%$/, ''))
    : value;
  if (typeof converted !== 'number' || !Number.isFinite(converted)) {
    throw new Error(`Missing/invalid number: ${context}`);
  }
  return converted;
}

function assertMatchingAuthoritativeFacts(input: ValidatedInput): void {
  const fhFacts = input.financialHealth.key_metrics.facts;
  const iaFacts = input.investmentAnalysis.key_metrics.facts;
  // All overlapping explicitly-labeled facts should agree. Extra facts are allowed.
  for (const section of ['cash', 'retirement', 'education'] as const) {
    const left = fhFacts[section] as Record<string, unknown> | undefined;
    const right = iaFacts[section] as Record<string, unknown> | undefined;
    if (!left || !right) continue;
    for (const [name, value] of Object.entries(left)) {
      if (!(name in right)) continue;
      const other = right[name];
      // Only compare the parts that define the meaning and value.
      for (const field of ['label', 'unit', 'value', 'min', 'max'] as const) {
        const a = (value as Record<string, unknown>)?.[field];
        const b = (other as Record<string, unknown>)?.[field];
        if (JSON.stringify(a) !== JSON.stringify(b)) {
          throw new Error(`Conflicting authoritative fact: ${section}.${name}.${field}`);
        }
      }
    }
  }
}

export function createFactRegistry(input: ValidatedInput): FactRegistry {
  assertMatchingAuthoritativeFacts(input);
  const { financialHealth: fh, investmentAnalysis: ia } = input;
  const registry: FactRegistry = {};

  function add(
    id: string,
    source: FinancialFact['source'],
    sourcePath: string,
    label: string,
    unit: FactUnit,
    guidance = '',
    options: { fractionToPercent?: boolean } = {},
  ) {
    const doc = source === 'financial-health' ? fh : ia;
    const value = getPath(doc, sourcePath);
    const rawValue = asNumber(value, `${source}:${sourcePath}`);
    registry[id] = {
      id, label,
      rawValue: options.fractionToPercent ? rawValue * 100 : rawValue,
      unit, source, sourcePath, guidance,
    };
  }

  function addOptional(
    id: string,
    source: FinancialFact['source'],
    sourcePath: string,
    label: string,
    unit: FactUnit,
    guidance = '',
    options: { fractionToPercent?: boolean } = {},
  ) {
    const doc = source === 'financial-health' ? fh : ia;
    const value = getPath(doc, sourcePath);
    if (value === undefined || value === null) return;
    const rawValue = asNumber(value, `${source}:${sourcePath}`);
    registry[id] = {
      id, label,
      rawValue: options.fractionToPercent ? rawValue * 100 : rawValue,
      unit, source, sourcePath, guidance,
    };
  }

  add('health.score', 'financial-health', 'score.published_score', 'Financial health score', 'score', 'Score is out of 100.');
  add('household.annualIncome', 'financial-health', 'key_metrics.ratios.debtToIncome.grossIncome', 'Annual gross household income', 'USD/yr');
  add('household.netWorth', 'financial-health', 'key_metrics.protection.umbrellaInsurance.assetExposed.netWorth', 'Household net worth', 'USD');
  add('retirement.fundingGap', 'investment-analysis', 'key_metrics.capacity.retirementGap', 'Projected retirement funding gap', 'USD', "In today's dollars; this is a projection, not a current account balance.");
  add('retirement.extraSavingsAnnual', 'financial-health', 'key_metrics.ratios.retirementSavings.requiredExtraSavings', 'Additional annual savings needed for retirement', 'USD/yr', 'Projection based on the report assumptions.');
  add('retirement.savingsCapacity', 'investment-analysis', 'key_metrics.facts.retirement.savingsCapacity.value', 'Annual savings capacity', 'USD/yr', 'Do not call this spare cash or free cash flow.');
  add('retirement.spendingNeed', 'financial-health', 'key_metrics.facts.retirement.spendingNeed.value', 'Yearly retirement spending need', 'USD/yr', 'Includes taxes, debt payments and goals; excludes projected long-term care.');
  add('retirement.incomeShare', 'financial-health', 'key_metrics.facts.retirement.incomeShareOfNeed.value', 'Share of retirement spending need covered by income', 'percent', 'This fact already contains percentage units; do not multiply by 100.');
  addOptional('retirement.savingsLeft', 'financial-health', 'key_metrics.facts.retirement.savingsLeftAtPlanEnd.value', 'Projected savings left at end of plan', 'USD', 'Projection, not guaranteed.');
  add('cash.accessible', 'financial-health', 'key_metrics.facts.cash.accessibleCash.value', 'Accessible cash', 'USD', 'Bank accounts plus accessible taxable money market. Do not include retirement cash.');
  add('cash.monthsCovered', 'financial-health', 'key_metrics.facts.cash.monthsCovered.value', 'Essential expenses covered by accessible cash', 'months');
  add('cash.emergencyReserveMin', 'financial-health', 'key_metrics.facts.cash.emergencyReserve.min', 'Minimum recommended emergency reserve', 'USD', 'Excludes near-term goals.');
  add('cash.totalCashTargetMin', 'financial-health', 'key_metrics.facts.cash.totalCashNeeded.min', 'Minimum total cash target', 'USD', 'Includes emergency reserve and near-term goals. Do not call this only emergency reserve.');
  add('cash.totalCashShortfall', 'financial-health', 'key_metrics.ratios.emergencyFund.shortfallToAdjustedMin', 'Gap to minimum total cash target', 'USD', 'Includes near-term goals.');
  addOptional('education.fundingGap', 'financial-health', 'key_metrics.facts.education.fundingGap.value', 'College funding gap', 'USD', 'Not a current payment or original education goal.');
  add('investments.return3y', 'investment-analysis', 'key_metrics.performanceAnalysis.household.return3yAnnualized', 'Annualized portfolio return over three years', 'percent', 'Historical performance; not a forecast.', { fractionToPercent: true });
  add('investments.drawdown3y', 'investment-analysis', 'key_metrics.performanceAnalysis.household.maxDrawdown3y', 'Largest three-year portfolio drawdown', 'percent', 'Negative value represents a past decline.', { fractionToPercent: true });
  addOptional('insurance.lifeDanielShortfall', 'financial-health', 'key_metrics.protection.lifeInsurance.lifeInsuranceCoverageGapsAndExcess.clientShortfall', 'Client life insurance shortfall', 'USD', 'Versus the minimum recommended coverage.');
  addOptional('insurance.lifeEmilyShortfall', 'financial-health', 'key_metrics.protection.lifeInsurance.lifeInsuranceCoverageGapsAndExcess.coClientShortfall', 'Co-client life insurance shortfall', 'USD', 'Versus the minimum recommended coverage.');
  addOptional('insurance.umbrellaGap', 'financial-health', 'key_metrics.protection.umbrellaInsurance.coverageRecommendationsAndAnalysis.umbrellaCoverageGap', 'Umbrella liability coverage gap', 'USD');

  const card = fh.profile && typeof fh.profile === 'object'
    ? ((fh.profile as Record<string, unknown>).liabilities as Array<Record<string, unknown>> | undefined)?.find((l) => l.type === 'PERSONAL_CREDIT_CARD')
    : undefined;
  if (card) {
    const interestRate = asNumber(card.interest_rate, 'credit card interest rate');
    registry['debt.cardBalance'] = {
      id: 'debt.cardBalance', label: 'Credit card balance',
      rawValue: asNumber(card.balance, 'credit card balance'), unit: 'USD',
      source: 'financial-health', sourcePath: 'profile.liabilities[type=PERSONAL_CREDIT_CARD].balance',
      guidance: 'Current debt, not annual payment.',
    };
    registry['debt.cardAPR'] = {
      id: 'debt.cardAPR', label: 'Credit card annual interest rate',
      rawValue: interestRate * 100, unit: 'percent',
      source: 'financial-health', sourcePath: 'profile.liabilities[type=PERSONAL_CREDIT_CARD].interest_rate',
      guidance: 'Annual credit card rate, not portfolio return.',
    };
  }

  // Cross-check prominent duplicate values, without conflating similarly named concepts.
  const crossChecks: Array<[string, unknown]> = [
    ['retirement.fundingGap', getPath(fh, 'key_metrics.ratios.retirementSavings.planningGapAtRetirementAgeInTodaysDollars')],
    ['retirement.extraSavingsAnnual', getPath(ia, 'key_metrics.savingsAndContributions.savingsCapacity.additionalAnnualSavingsNeededToCloseGap')],
    ['cash.totalCashShortfall', getPath(ia, 'key_metrics.cashNeeds.accessibleCashGap')],
  ];
  for (const [id, other] of crossChecks) {
    if (other === undefined) continue;
    if (Math.abs(registry[id]!.rawValue - asNumber(other, id)) > 0.01) {
      throw new Error(`Conflicting report values for ${id}.`);
    }
  }

  return registry;
}

export function formatFact(fact: FinancialFact): string {
  const value = fact.rawValue;
  if (fact.unit === 'score') return `${Math.round(value)} out of 100`;
  if (fact.unit === 'percent') {
    const precision = Math.abs(value % 1) > 0.001 ? 1 : 0;
    return `${value.toFixed(precision)}%`;
  }
  if (fact.unit === 'months') return `${value.toFixed(1)} months`;
  const formatted = new Intl.NumberFormat('en-US', {maximumFractionDigits: 0}).format(value);
  if (fact.unit === 'USD/yr') return `$${formatted} per year`;
  return `$${formatted}`;
}
