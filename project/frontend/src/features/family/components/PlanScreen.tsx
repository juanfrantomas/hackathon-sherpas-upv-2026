import { useEffect, useRef } from 'react'
import { DemoTag } from '../../../components/ui/DemoTag'
import { Icon } from '../../../components/ui/Icon'
import { ScreenHeader } from './ScreenHeader'
import { PlanRecommendation } from './PlanRecommendation'
import { PLAN_DISCLAIMER, PLAN_SECTIONS } from '../data/planSections'
import type { Family, Navigate, NavigationState, PlanSectionId } from '../types'

export interface PlanScreenProps {
  family: Family
  nav: NavigationState
  setNav: (nav: Partial<NavigationState>) => void
  go: Navigate
}

/** Screen 5 — the household's Sherpas plan, section by section. */
export function PlanScreen({ family, nav, setNav, go }: PlanScreenProps) {
  const section = nav.planSection || 'summary'
  const sectionData = family.sections[section] ?? { pending: true }
  const stripRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    stripRef.current
      ?.querySelector('.is-on')
      ?.scrollIntoView?.({
        inline: 'center',
        block: 'nearest',
        behavior: 'smooth',
      })
  }, [section])

  const sectionLabel =
    PLAN_SECTIONS.find((entry) => entry.id === section)?.label ?? section

  return (
    <div className="screen screen--tabbed">
      <ScreenHeader
        title="My Financial Plan"
        right={
          <button
            className="icon-btn"
            aria-label="Ask the mentor"
            onClick={() => go('mentor', { from: 'plan' })}
          >
            <Icon name="mic" size={21} />
          </button>
        }
      />

      <div className="plan-strip" ref={stripRef}>
        {PLAN_SECTIONS.map((entry) => (
          <button
            key={entry.id}
            className={`pill${section === entry.id ? ' is-on' : ''}`}
            onClick={() => setNav({ planSection: entry.id as PlanSectionId, planCard: null })}
          >
            {entry.label}
          </button>
        ))}
      </div>

      <div className="pad stack-4" key={section}>
        {section === 'summary' && (
          <div className="facts">
            {family.facts.map((fact) => (
              <div className="fact" key={fact.label}>
                <span>{fact.label}</span>
                <strong className="num">{fact.value}</strong>
                {fact.sub && <em>{fact.sub}</em>}
              </div>
            ))}
          </div>
        )}

        {sectionData.pending ? (
          <div className="pending">
            <Icon name="plan" size={22} />
            <h3>{sectionLabel}</h3>
            <p className="small muted">
              This section of your Sherpas plan will appear here. The hackathon case
              data doesn't include details for it, so nothing is shown rather
              than estimated.
            </p>
            <DemoTag>Placeholder</DemoTag>
          </div>
        ) : (
          sectionData.cards?.map((card) => (
            <PlanRecommendation
              key={card.id}
              family={family}
              card={card}
              open={nav.planCard === card.id}
              onToggle={() =>
                setNav({ planCard: nav.planCard === card.id ? null : card.id })
              }
              go={go}
            />
          ))
        )}

        <p className="disclaimer">
          <Icon name="info" size={14} /> {PLAN_DISCLAIMER}
        </p>
      </div>
    </div>
  )
}
