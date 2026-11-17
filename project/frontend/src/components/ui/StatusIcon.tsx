import { Icon } from './Icon'
import type { MilestoneStatus } from '../../features/family/types'

export interface StatusIconProps {
  status: MilestoneStatus
  size?: number
}

/** Round glyph that encodes a milestone's status. */
export function StatusIcon({ status, size = 28 }: StatusIconProps) {
  if (status === 'completed') {
    return (
      <span className="st st--done" style={{ width: size, height: size }}>
        <Icon name="check" size={size * 0.55} stroke={2.4} />
      </span>
    )
  }

  if (status === 'in_progress') {
    return (
      <span className="st st--now" style={{ width: size, height: size }}>
        <span />
      </span>
    )
  }

  if (status === 'needs_review') {
    return (
      <span className="st st--review" style={{ width: size, height: size }}>
        <Icon name="flag" size={size * 0.5} stroke={2} />
      </span>
    )
  }

  return <span className="st st--todo" style={{ width: size, height: size }} />
}
