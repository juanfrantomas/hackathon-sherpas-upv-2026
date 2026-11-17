import { JOURNEY } from '../features/family/data/journey'
import type { FamilyScreen, Navigate } from '../features/family/types'

export interface JourneyRailProps {
  /** The step that matches the current screen, if any. */
  activeStepId: string | undefined
  go: Navigate
}

/** The left-hand rail that drives the phone through the demo journey. */
export function JourneyRail({ activeStepId, go }: JourneyRailProps) {
  return (
    <aside className="flow">
      <h2 className="micro flow__h">Journey</h2>
      <ol>
        {JOURNEY.map((step) => (
          <li key={step.id}>
            <button
              className={activeStepId === step.id ? 'is-on' : ''}
              onClick={() => go(step.screen, { ...step.opts, from: 'home' })}
            >
              <span className="num">{step.n}</span>
              {step.label}
            </button>
          </li>
        ))}
      </ol>
      <p className="micro muted flow__note">Everything in the phone is clickable.</p>
    </aside>
  )
}

export type { FamilyScreen }
