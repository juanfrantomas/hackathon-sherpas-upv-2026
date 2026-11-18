import { Button } from '../../../components/ui/Button'
import { Icon } from '../../../components/ui/Icon'
import { PlanChart } from '../../../components/charts/PlanChart'
import { useFamilyData } from '../state/useFamily'
import type { Family, Navigate, PlanCard } from '../types'

export interface PlanRecommendationProps {
  family: Family
  card: PlanCard
  open: boolean
  onToggle: () => void
  go: Navigate
}

/**
 * One recommendation from the plan: a question, the reason it matters, and the
 * next action. Collapsed it shows only the headline; expanded it shows the
 * full "what / why / next" answer and a chart.
 */
export function PlanRecommendation({
  family,
  card,
  open,
  onToggle,
  go,
}: PlanRecommendationProps) {
  const { milestones } = useFamilyData()

  // Cards point at static demo ids. Milestones from the backend have their own
  // ids, so fall back to the first milestone of the card's plan section.
  const sectionId = Object.entries(family.sections).find(([, section]) =>
    section.cards?.some((c) => c.id === card.id),
  )?.[0]
  const milestoneTarget =
    milestones.find((m) => m.id === card.milestone)?.id ??
    milestones.find((m) => m.section === sectionId)?.id

  return (
    <div className={`rec${open ? ' is-open' : ''}`}>
      <button className="rec__head" onClick={onToggle} aria-expanded={open}>
        <div className="grow">
          <h3>{card.title}</h3>
          {!open && <p className="small muted">{card.what}</p>}
        </div>
        <Icon name="chevronDown" size={20} className="rec__chev" />
      </button>

      {card.chart && (
        <div className="rec__chart">
          <PlanChart kind={card.chart} family={family} />
        </div>
      )}

      {open && (
        <div className="rec__body">
          <ol className="qa">
            <li>
              <span className="qa__q">What is happening?</span>
              <p>{card.what}</p>
            </li>
            <li>
              <span className="qa__q">Why does it matter to my family?</span>
              <p>{card.why}</p>
            </li>
            <li>
              <span className="qa__q">What should I do next?</span>
              <p>{card.next}</p>
            </li>
          </ol>
          <div className="row-2">
            <Button
              variant="secondary"
              icon="mic"
              onClick={() => go('mentor', { from: 'plan', topic: card.title })}
            >
              Ask the mentor
            </Button>
            {card.milestone && (
              <Button
                variant="ghost"
                iconRight="arrowRight"
                onClick={() =>
                  go('progress', { tab: 'milestones', open: milestoneTarget })
                }
              >
                Go to milestone
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
