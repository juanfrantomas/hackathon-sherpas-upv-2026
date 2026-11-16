import { z } from 'zod';

/** The accepted contract supports schema v2; unknown report fields remain intact. */
const Identifier = z.object({
  slug: z.string().min(1),
  household: z.array(z.object({
    first_name: z.string().min(1),
    role: z.string().min(1),
  }).passthrough()).min(1),
}).passthrough();

const Fact = z.object({
  label: z.string().min(1),
  unit: z.string().min(1),
  value: z.union([z.string(), z.number()]).optional(),
  min: z.number().optional(),
  max: z.number().optional(),
  notToBeConfusedWith: z.array(z.string()).optional(),
}).passthrough();

const Facts = z.object({
  rules: z.array(z.string()).min(1),
  cash: z.object({
    accessibleCash: Fact,
    monthsCovered: Fact,
    emergencyReserve: Fact,
    totalCashNeeded: Fact,
  }).passthrough(),
  retirement: z.object({
    spendingNeed: Fact,
    spendingGap: Fact,
    savingsLeftAtPlanEnd: Fact,
    incomeShareOfNeed: Fact,
  }).passthrough(),
  education: z.object({ fundingGap: Fact }).passthrough(),
}).passthrough();

const CoreDocument = z.object({
  schema_version: z.literal(2),
  case: Identifier,
  narrative: z.record(z.string(), z.unknown()),
  key_metrics: z.object({ facts: Facts }).passthrough(),
}).passthrough();

export const FinancialHealthSchema = CoreDocument.extend({
  part: z.literal('financial-health'),
  score: z.object({
    published_score: z.number().min(0).max(100),
    band: z.string(),
  }).passthrough(),
});

export const InvestmentAnalysisSchema = CoreDocument.extend({
  part: z.literal('investment-analysis'),
});

export type FinancialHealth = z.infer<typeof FinancialHealthSchema>;
export type InvestmentAnalysis = z.infer<typeof InvestmentAnalysisSchema>;

export type ValidatedInput = {
  financialHealth: FinancialHealth;
  investmentAnalysis: InvestmentAnalysis;
  personaMarkdown: string;
};

export function validateDocuments(
  financialHealth: unknown,
  investmentAnalysis: unknown,
  personaMarkdown: string,
): ValidatedInput {
  const fh = FinancialHealthSchema.parse(financialHealth);
  const ia = InvestmentAnalysisSchema.parse(investmentAnalysis);
  if (fh.case.slug !== ia.case.slug) {
    throw new Error('Both JSON files must describe the same case.slug.');
  }
  const names = (h: typeof fh.case.household) =>
    h.map((person) => `${person.role}:${person.first_name}`).sort().join('|');
  if (names(fh.case.household) !== names(ia.case.household)) {
    throw new Error('Both JSON files must describe the same household.');
  }
  if (!personaMarkdown.trim()) throw new Error('persona.md cannot be empty.');
  if (personaMarkdown.length > 40_000) throw new Error('persona.md is too large (40 KB maximum).');
  return { financialHealth: fh, investmentAnalysis: ia, personaMarkdown };
}
