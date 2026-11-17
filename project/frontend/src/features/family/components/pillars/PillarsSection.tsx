import { Card } from '../../../../components/ui/Card'
import { Chip } from '../../../../components/ui/Chip'
import { Eyebrow } from '../../../../components/ui/Eyebrow'
import { usePillars } from '../../hooks/usePillars'
import type { Family } from '../../types'

export interface PillarsSectionProps {
  family: Family
}

/**
 * The four pillars of the plan.
 *
 * They answer what would change if the household acted, what the mentor
 * thinks of them today, how the two of them can agree, and where they come
 * from.  Everything is read from the backend, which writes the words from
 * the plan itself.
 */
export function PillarsSection({ family }: PillarsSectionProps) {
  const { simulator, insights, couple, story, activeIds, toggleDecision, loading } =
    usePillars(family.caseId)

  if (loading && !simulator) {
    return (
      <Card tone="soft" className="stack-3">
        <Eyebrow>Your plan, explained</Eyebrow>
        <p className="small muted">Reading your plan…</p>
      </Card>
    )
  }

  return (
    <div className="stack-3">
      {/* 1. The decision laboratory */}
      {simulator && (
        <Card tone="soft" className="stack-3">
          <Eyebrow>What if you decided differently?</Eyebrow>
          <h3 className="h4">
            Your score would move from {simulator.score_base} to{' '}
            {simulator.simulated_score}
          </h3>
          <p className="small muted">{simulator.visual_summary}</p>
          <div className="row-wrap">
            {simulator.power_ups.map((powerUp) => (
              <button
                key={powerUp.id}
                type="button"
                className={`pill-btn ${powerUp.active ? 'is-on' : ''}`}
                onClick={() => toggleDecision(powerUp.id)}
                aria-pressed={powerUp.active}
              >
                {powerUp.icon} {powerUp.title}
              </button>
            ))}
          </div>
          {simulator.synergy_detected && (
            <p className="small">
              <strong>{simulator.synergy_message}</strong>
            </p>
          )}
          {simulator.timeline_comparison.length > 0 && (
            <div className="stack-2">
              {simulator.timeline_comparison.slice(0, 2).map((moment) => (
                <div key={moment.milestone} className="small stack-1">
                  <strong>
                    {moment.icon} {moment.milestone}
                  </strong>
                  <span className="muted">{moment.without_changes}</span>
                  <span>{moment.with_decisions}</span>
                  <Chip tone="ok">{moment.highlighted_change}</Chip>
                </div>
              ))}
            </div>
          )}
          {activeIds.length > 0 && (
            <p className="micro muted">
              {activeIds.length} decision{activeIds.length === 1 ? '' : 's'} switched
              on.
            </p>
          )}
        </Card>
      )}

      {/* 2. The proactive mentor */}
      {insights && insights.proactive_nudge.message && (
        <Card tone="soft" className="stack-2">
          <Eyebrow>{insights.proactive_nudge.badge || 'From your mentor'}</Eyebrow>
          <h3 className="h4">{insights.proactive_nudge.greeting}</h3>
          <p className="small">{insights.proactive_nudge.message}</p>
          {insights.jargon_pills.slice(0, 2).map((pill) => (
            <div key={pill.term} className="small stack-1">
              <strong>{pill.term}</strong>
              <span className="muted">{pill.metaphor_title}</span>
              <span>{pill.metaphor_explanation}</span>
            </div>
          ))}
        </Card>
      )}

      {/* 3. The couple */}
      {couple && couple.is_couple && couple.members.length >= 2 && (
        <Card tone="soft" className="stack-2">
          <Eyebrow>As a couple</Eyebrow>
          <p className="small">{couple.consensus_bridge}</p>
          <div className="row-wrap">
            {couple.members.map((member) => (
              <Chip key={member.key} tone="blue">
                {member.name} · {member.risk_profile}
              </Chip>
            ))}
          </div>
          {couple.high_fives.length > 0 && (
            <p className="small muted">
              {couple.high_fives.length} high five
              {couple.high_fives.length === 1 ? '' : 's'} on the wall.
            </p>
          )}
        </Card>
      )}

      {/* 4. The story */}
      {story && story.scenes.length > 0 && (
        <Card tone="soft" className="stack-2">
          <Eyebrow>Your financial story</Eyebrow>
          <p className="small">{story.main_challenge}</p>
          {story.scenes.slice(0, 2).map((scene) => (
            <div key={scene.scene_id} className="small stack-1">
              <strong>
                {scene.headline_figure} · {scene.title}
              </strong>
              <span className="muted">{scene.subtitle}</span>
              <span>{scene.caption_narration}</span>
            </div>
          ))}
        </Card>
      )}
    </div>
  )
}
