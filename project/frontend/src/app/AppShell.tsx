import { useEffect, useRef } from 'react'
import { SegmentedControl } from '../components/ui/SegmentedControl'
import { Wordmark } from '../components/brand/Wordmark'
import { DesignSystemPage } from '../features/design-system/DesignSystemPage'
import { JOURNEY } from '../features/family/data/journey'
import { FAMILIES } from '../features/family/data/families'
import { useFamilyData, useNavigation } from '../features/family/state/useFamily'
import { useBackendStatus } from '../features/family/state/useBackendStatus'
import type { PrototypeMode } from '../features/family/types'
import { FamilyPhone } from './FamilyPhone'
import { JourneyRail } from './JourneyRail'
import { PrototypeControls } from './PrototypeControls'
import { PROTOTYPE_MODES } from './prototypeModes'

const BACKEND_STATUS_LABEL = {
  off: { text: 'Demo data', hint: 'No backend configured (VITE_MILESTONES_API_URL)' },
  checking: { text: 'Connecting…', hint: 'Checking the backend' },
  connected: { text: 'Connected to backend', hint: 'Milestones come from the backend' },
  offline: { text: 'Backend offline', hint: 'Showing the static demo data' },
} as const

export interface AppShellProps {
  mode: PrototypeMode
  onModeChange: (mode: PrototypeMode) => void
}

/** The prototype shell: top bar, journey rail, phone and prototype controls. */
export function AppShell({ mode, onModeChange }: AppShellProps) {
  const { family, dispatch } = useFamilyData()
  const { screen, nav, go } = useNavigation()
  const backend = useBackendStatus()

  const scrollRef = useRef<HTMLDivElement>(null)

  // Every screen change starts the phone at the top.
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0
  }, [screen, nav.progressTab, nav.planSection])

  const selectFamily = (id: string) => {
    const selected = FAMILIES.find((option) => option.id === id)
    if (selected) {
      dispatch({ type: 'select_family', familyId: selected.id })
    }
  }

  const resetDemo = () => {
    dispatch({ type: 'reset_all' })
  }

  const activeStep = JOURNEY.find(
    (step) =>
      step.screen === screen &&
      (step.screen !== 'progress' ||
        step.opts?.tab === (nav.progressTab || 'milestones')),
  )

  return (
    <div className="proto">
      <header className="proto-bar">
        <div className="proto-bar__brand">
          <Wordmark size="sm" />
          <span className="proto-bar__tag">Hackathon prototype</span>
        </div>

        <SegmentedControl<PrototypeMode>
          size="sm"
          value={mode}
          onChange={onModeChange}
          options={PROTOTYPE_MODES.map((option) => ({ ...option }))}
        />

        <span
          className={`backend-status backend-status--${backend}`}
          role="status"
          title={BACKEND_STATUS_LABEL[backend].hint}
        >
          <span className="backend-status__dot" aria-hidden="true" />
          {BACKEND_STATUS_LABEL[backend].text}
        </span>

        <label className="fam-select" htmlFor="fam">
          <span className="micro muted">Demo family</span>
          <select
            id="fam"
            value={family.id}
            onChange={(event) => selectFamily(event.target.value)}
          >
            {FAMILIES.map((option) => (
              <option key={option.id} value={option.id}>
                {option.names} {option.surname} · score {option.score}
              </option>
            ))}
          </select>
        </label>
      </header>

      {mode === 'family' ? (
        <div className="stage">
          <JourneyRail activeStepId={activeStep?.id} go={go} />

          <FamilyPhone scrollRef={scrollRef} />

          <PrototypeControls
            family={family}
            onReset={resetDemo}
          />
        </div>
      ) : (
        <DesignSystemPage />
      )}
    </div>
  )
}
