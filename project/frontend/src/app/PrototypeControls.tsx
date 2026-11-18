import { Icon } from '../components/ui/Icon'
import type { Family } from '../features/family/types'

export interface PrototypeControlsProps {
  family: Family
  /** Restores every household's local state. */
  onReset: () => void
}

/** The right-hand panel: the household and the reset. */
export function PrototypeControls({ family, onReset }: PrototypeControlsProps) {
  return (
    <aside className="controls">
      <h2 className="micro flow__h">Prototype controls</h2>

      <div className="ctl-block">
        <strong className="small">
          {family.names} {family.surname}
        </strong>
        <p className="micro muted">
          {family.challenge}. Facts from the hackathon case only.
        </p>
      </div>

      <div className="ctl-block">
        <button className="btn btn--ghost btn--sm btn--block" onClick={onReset}>
          <Icon name="replay" size={16} />
          <span>Reset</span>
        </button>
      </div>
    </aside>
  )
}
