import type { SegmentedOption } from '../components/ui/SegmentedControl'
import type { PrototypeMode } from '../features/family/types'

/** The two areas the prototype shell can show. */
export const PROTOTYPE_MODES = [
  { value: 'family', label: 'Family app', icon: 'home' },
  { value: 'system', label: 'Design system', icon: 'grid' },
] as const satisfies ReadonlyArray<SegmentedOption<PrototypeMode>>
