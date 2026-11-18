import { useState } from 'react'
import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { Chip } from '../../../components/ui/Chip'
import { DemoTag } from '../../../components/ui/DemoTag'
import { Eyebrow } from '../../../components/ui/Eyebrow'
import { Icon } from '../../../components/ui/Icon'
import { SegmentedControl } from '../../../components/ui/SegmentedControl'
import { StatusIcon } from '../../../components/ui/StatusIcon'
import { STATUS_META } from '../../../components/ui/statusMeta'
import { ScreenHeader } from './ScreenHeader'
import { useFamilyData } from '../state/useFamily'
import { MilestoneItem } from './MilestoneItem'
import { PillarsSection } from './pillars/PillarsSection'
import type {
  FamilyState,
  MilestoneStatus,
  Navigate,
  NavigationState,
  ProgressTab,
} from '../types'
import type { MilestoneWithStatus } from '../state/selectors'

export interface ProgressScreenProps {
  state: FamilyState
  milestones: MilestoneWithStatus[]
  nav: NavigationState
  setNav: (nav: Partial<NavigationState>) => void
  setStatus: (milestoneId: string, status: MilestoneStatus) => void
  go: Navigate
}

/** Screen 6 and 8 — the household's milestones and the journey overview. */
export function ProgressScreen({
  state,
  milestones,
  nav,
  setNav,
  setStatus,
  go,
}: ProgressScreenProps) {
  const tab: ProgressTab = nav.progressTab || 'milestones'
  const [justDone, setJustDone] = useState<string | null>(null)
  const { family, milestonesStale, milestonesError } = useFamilyData()

  const completed = milestones.filter((milestone) => milestone.status === 'completed')
  const pending = milestones.filter((milestone) => milestone.status !== 'completed')

  const handleStatus = (milestoneId: string, status: MilestoneStatus) => {
    setStatus(milestoneId, status)
    setJustDone(status === 'completed' ? milestoneId : null)
  }

  return (
    <div className="screen screen--tabbed">
      <ScreenHeader title="Progress" />

      <div className="pad stack-4">
        {(milestonesStale || milestonesError) && (
          <p className="small warn-text" role="status">
            {milestonesError ?? 'These milestones may be older than your latest plan.'}
          </p>
        )}
        <SegmentedControl<ProgressTab>
          value={tab}
          onChange={(value) => setNav({ progressTab: value })}
          options={[
            { value: 'milestones', label: 'Milestones' },
            { value: 'journey', label: 'Journey' },
          ]}
        />

        {tab === 'milestones' ? (
          <>
            <div className="ms-sum">
              <div>
                <h2 className="h3">Your steps from the plan</h2>
                <p className="small muted">
                  {completed.length} of {milestones.length} complete. Move at your own
                  pace.
                </p>
              </div>
              <DemoTag>Demo progress</DemoTag>
            </div>

            <ol className="ms-list">
              {milestones.map((milestone, index) => (
                <MilestoneItem
                  key={milestone.id}
                  milestone={milestone}
                  last={index === milestones.length - 1}
                  justDone={justDone === milestone.id}
                  open={nav.openMilestone === milestone.id}
                  onToggle={() =>
                    setNav({
                      openMilestone: nav.openMilestone === milestone.id ? null : milestone.id,
                    })
                  }
                  setStatus={handleStatus}
                  go={go}
                />
              ))}
            </ol>
          </>
        ) : (
          <>
            <Card tone="soft" className="journey-sum">
              <Eyebrow>So far</Eyebrow>
              <h2 className="h3">
                {completed.length === 0
                  ? "You've started. Understanding your plan is the first step."
                  : completed.length === milestones.length
                    ? 'Every step in your plan is complete.'
                    : `You've completed ${completed.length} ${
                        completed.length === 1 ? 'step' : 'steps'
                      } from your plan.`}
              </h2>
              <p className="small muted">
                {state.watched
                  ? "You've watched your financial story"
                  : 'Your financial story is ready to watch'}
                {state.checkins.length
                  ? ` and completed ${state.checkins.length} check-in${
                      state.checkins.length > 1 ? 's' : ''
                    }.`
                  : '.'}
              </p>
              <DemoTag>Demo progress</DemoTag>
            </Card>

            <section className="tl">
              <h3 className="tl__h">Coming up</h3>
              <button className="tl__item" onClick={() => go('checkin')}>
                <span className="tl__dot tl__dot--blue" />
                <div className="grow">
                  <strong>Monthly check-in</strong>
                  <span className="small muted">
                    {state.nextCheckin} · about two minutes
                  </span>
                </div>
                <Chip tone="blue">Start</Chip>
              </button>

              {pending.slice(0, 2).map((milestone) => (
                <button
                  key={milestone.id}
                  className="tl__item"
                  onClick={() =>
                    setNav({ progressTab: 'milestones', openMilestone: milestone.id })
                  }
                >
                  <span className="tl__dot" />
                  <div className="grow">
                    <strong>{milestone.title}</strong>
                    <span className="small muted">
                      {STATUS_META[milestone.status].label}
                      {milestone.checkin ? ` · check-in ${milestone.checkin}` : ''}
                    </span>
                  </div>
                  <Icon name="chevronRight" size={16} className="muted" />
                </button>
              ))}

              {state.reviewRequested && (
                <div className="tl__item">
                  <span className="tl__dot tl__dot--warn" />
                  <div className="grow">
                    <strong>Plan review requested</strong>
                    <span className="small muted">Your advisor will follow up</span>
                  </div>
                </div>
              )}
            </section>

            <section className="tl">
              <h3 className="tl__h">Recent check-ins</h3>
              {state.checkins.length === 0 && (
                <p className="small muted tl__empty">
                  No check-ins yet. Your first one is on {state.nextCheckin}.
                </p>
              )}
              {[...state.checkins].reverse().map((checkin, index) => (
                <div className="tl__item" key={`${checkin.date}-${index}`}>
                  <span className="tl__dot tl__dot--ok" />
                  <div className="grow">
                    <strong>{checkin.summary}</strong>
                    <span className="small muted">
                      {checkin.date}
                      {checkin.shared ? ' · shared with advisor' : ' · private'}
                    </span>
                  </div>
                </div>
              ))}
            </section>

            <section className="tl">
              <h3 className="tl__h">Completed</h3>
              {completed.length === 0 && (
                <p className="small muted tl__empty">
                  Completed steps will collect here so you can look back.
                </p>
              )}
              {completed.map((milestone) => (
                <button
                  key={milestone.id}
                  className="tl__item"
                  onClick={() =>
                    setNav({ progressTab: 'milestones', openMilestone: milestone.id })
                  }
                >
                  <StatusIcon status="completed" size={20} />
                  <div className="grow">
                    <strong>{milestone.title}</strong>
                    <span className="small muted">Revisit what you learned</span>
                  </div>
                  <Icon name="chevronRight" size={16} className="muted" />
                </button>
              ))}
            </section>

            <PillarsSection family={family} />

            <Button
              block
              variant="secondary"
              icon="calendar"
              onClick={() => go('checkin')}
            >
              Start your check-in
            </Button>
          </>
        )}
      </div>
    </div>
  )
}
