import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { DemoTag } from '../../../components/ui/DemoTag'
import { Eyebrow } from '../../../components/ui/Eyebrow'
import { Icon } from '../../../components/ui/Icon'
import { ScoreRing } from '../../../components/ui/ScoreRing'
import { Wordmark } from '../../../components/brand/Wordmark'
import { greetingFor } from '../utils/greeting'
import type { Family, FamilyState, Navigate } from '../types'
import type { MilestoneWithStatus } from '../state/selectors'

export interface HomeDashboardProps {
  family: Family
  state: FamilyState
  milestones: MilestoneWithStatus[]
  current: MilestoneWithStatus | undefined
  go: Navigate
}

/** Screen 3 — the household's dashboard. */
export function HomeDashboard({
  family,
  state,
  milestones,
  current,
  go,
}: HomeDashboardProps) {
  const firstCardId = family.sections[family.nextStep.section]?.cards?.[0]?.id

  return (
    <div className="screen screen--tabbed">
      <header className="home-head">
        <Wordmark size="sm" />
        <div className="home-head__actions">
          <button
            className="icon-btn has-dot"
            aria-label="Notifications: check-in available"
          >
            <Icon name="bell" size={21} />
          </button>
          <button className="avatar" aria-label="Profile">
            {family.initials}
          </button>
        </div>
      </header>

      <div className="pad stack-5">
        <div>
          <p className="muted small">{greetingFor()},</p>
          <h1 className="h-title">{family.names}</h1>
        </div>

        <Card className="score-card" onClick={() => go('plan', { section: 'summary' })}>
          <ScoreRing score={family.score} size={92} stroke={8} />
          <div className="score-card__text">
            <Eyebrow>Financial health score</Eyebrow>
            <p className="small">{family.scoreNote}</p>
            <span className="score-card__link">
              How it's calculated <Icon name="chevronRight" size={14} />
            </span>
          </div>
        </Card>

        <section className="stack-3">
          <div className="sec-head">
            <h2>Main priority</h2>
          </div>
          <p className="priority">{family.challenge}</p>
          <div className="focus-row">
            {family.focusAreas.map((area) => (
              <div key={area.label} className={`focus focus--${area.tone}`}>
                <span>{area.label}</span>
                <strong className="num">{area.detail}</strong>
              </div>
            ))}
          </div>
        </section>

        <Card tone="accent" className="next-step">
          <Eyebrow>Your next step</Eyebrow>
          <h3>{family.nextStep.title}</h3>
          <p className="small">{family.nextStep.why}</p>
          <div className="row-2">
            <Button
              size="md"
              iconRight="arrowRight"
              onClick={() =>
                go('plan', { section: family.nextStep.section, card: firstCardId })
              }
            >
              Explore
            </Button>
            <Button
              size="md"
              variant="ghost"
              icon="mic"
              onClick={() => go('mentor', { from: 'home', topic: family.nextStep.topic })}
            >
              Ask about it
            </Button>
          </div>
        </Card>

        <section className="stack-3">
          <div className="sec-head">
            <h2>Your journey</h2>
            <button
              className="link-btn"
              onClick={() => go('progress', { tab: 'milestones' })}
            >
              See all
            </button>
          </div>
          <Card
            className="journey-mini"
            onClick={() => go('progress', { tab: 'milestones', open: current?.id })}
          >
            <div className="journey-mini__track">
              {milestones.map((milestone) => (
                <span
                  key={milestone.id}
                  className={`jm-dot jm-dot--${milestone.status}`}
                  title={milestone.title}
                />
              ))}
            </div>
            <div className="journey-mini__now">
              <span className="muted micro">Now</span>
              <strong>{current ? current.title : 'All steps complete'}</strong>
            </div>
            <Icon name="chevronRight" size={18} className="muted" />
          </Card>
        </section>

        <Card className="review-row" onClick={() => go('checkin')}>
          <span className="review-row__ic">
            <Icon name="calendar" size={20} />
          </span>
          <div className="grow">
            <Eyebrow>Next check-in</Eyebrow>
            <strong>Monthly check-in · {state.nextCheckin}</strong>
            <p className="small muted">
              A two-minute look at {family.checkinPriority}.
            </p>
          </div>
          <DemoTag>Demo date</DemoTag>
        </Card>

        <button className="mentor-cta" onClick={() => go('mentor', { from: 'home' })}>
          <span className="mentor-cta__orb">
            <Icon name="mic" size={22} stroke={1.8} />
          </span>
          <span className="grow">
            <strong>Talk about your plan</strong>
            <span className="small">
              Your mentor knows your plan and goals. Interrupt anytime.
            </span>
          </span>
          <Icon name="chevronRight" size={18} />
        </button>
      </div>
    </div>
  )
}
