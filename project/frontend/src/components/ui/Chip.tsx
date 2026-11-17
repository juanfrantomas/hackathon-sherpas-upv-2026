import type { ReactNode } from 'react'
import { Icon } from './Icon'
import type { IconName } from './iconPaths'
import type { Tone } from '../../features/family/types'

export interface ChipProps {
  tone?: Tone
  icon?: IconName
  children: ReactNode
}

/** Small status pill, e.g. "In progress" or "Needs review". */
export function Chip({ tone = 'neutral', icon, children }: ChipProps) {
  return (
    <span className={`chip chip--${tone}`}>
      {icon && <Icon name={icon} size={13} stroke={2} />}
      {children}
    </span>
  )
}
