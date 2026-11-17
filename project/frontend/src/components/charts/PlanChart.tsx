import { ScoreRing } from '../ui/ScoreRing'
import { CashDebtBars } from './CashDebtBars'
import { GoalTimeline } from './GoalTimeline'
import { TwoGoals } from './TwoGoals'
import type { ChartKind, Family } from '../../features/family/types'

export interface PlanChartProps {
  kind: ChartKind
  family: Family
}

/**
 * Renders the chart that accompanies a plan recommendation.
 * Every variant plots values stated in the plan; nothing is projected.
 */
export function PlanChart({ kind, family }: PlanChartProps) {
  switch (kind) {
    case 'cashDebt':
      return <CashDebtBars />

    case 'timelineCarter':
      return (
        <GoalTimeline
          caption="Goals from your plan. Retirement year depends on your age, shown as stated."
          points={[
            { k: 'Today', v: 'Score 26', now: true },
            { k: '2027', v: '$550,000 home' },
            { k: 'Age 58', v: 'Retire' },
          ]}
        />
      )

    case 'timelineLewis':
      return (
        <GoalTimeline
          caption="Commitments from your plan."
          points={[
            { k: 'Today', v: 'No debt', now: true },
            { k: 'Now', v: 'College begins' },
            { k: '2030', v: 'Second home' },
          ]}
        />
      )

    case 'twoGoals':
      return <TwoGoals />

    case 'score':
      return (
        <figure className="chart chart--score">
          <ScoreRing score={family.score} size={84} stroke={7} />
          <figcaption>Financial health score from Sherpas.</figcaption>
        </figure>
      )
  }
}
