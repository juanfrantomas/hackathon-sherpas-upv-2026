export type PersonaContext = {
  wealthTier?: string;
  lifeStage?: string;
  severity?: string;
  riskAlignment?: string;
  decisionStyle?: string;
  motivationalAnchor?: string;
  motivationConfidence: 'low' | 'unspecified';
  subjectiveConcernsRecorded: boolean;
};

/**
 * Only qualitative metadata goes to the LLM. Financial numbers appearing in
 * persona.md are not accepted as financial evidence.
 */
export function parsePersona(markdown: string): PersonaContext {
  const classification = markdown.match(/```classification\s*([\s\S]*?)```/i)?.[1] ?? '';
  const get = (key: string) => classification.match(new RegExp(`^${key}:\\s*(.+)$`, 'mi'))?.[1]?.trim();
  const motivationSection = markdown.match(/## D6:[^\n]*\n([\s\S]*?)(?=\n## |$)/i)?.[1] ?? '';
  const subjective = markdown.match(/## Subjective concerns[^\n]*\n([\s\S]*?)(?=\n## |$)/i)?.[1] ?? '';
  return {
    wealthTier: get('D0'),
    lifeStage: get('D1'),
    severity: get('D3'),
    riskAlignment: get('D4'),
    decisionStyle: get('D5'),
    motivationalAnchor: get('D6'),
    motivationConfidence: /provisional|confidence is low/i.test(motivationSection) ? 'low' : 'unspecified',
    subjectiveConcernsRecorded: subjective.length > 0 && !/none recorded/i.test(subjective),
  };
}
