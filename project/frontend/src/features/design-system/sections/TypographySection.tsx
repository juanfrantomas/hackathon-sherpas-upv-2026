import { Eyebrow } from '../../../components/ui/Eyebrow'
import { ApproxBadge } from '../ApproxBadge'

/** The type scale, in Inter. */
export function TypographySection() {
  return (
    <section className="ds-sec">
      <h2 className="h3">
        Typography · Inter <ApproxBadge />
      </h2>
      <div className="type-scale">
        <div>
          <code className="micro">Display 28/34 · 600</code>
          <span className="h-display">Your Financial Story</span>
        </div>
        <div>
          <code className="micro">Title 22/28 · 600</code>
          <span className="h-title">Timothy &amp; Melanie</span>
        </div>
        <div>
          <code className="micro">Heading 17/24 · 600</code>
          <span className="h3">Understand your credit card debt</span>
        </div>
        <div>
          <code className="micro">Body 15/22 · 400</code>
          <span>
            You hold $150,000 in cash while carrying $18,000 on credit cards.
          </span>
        </div>
        <div>
          <code className="micro">Small 13/18 · 400</code>
          <span className="small">
            Rules-based diagnostic from provided data and assumptions.
          </span>
        </div>
        <div>
          <code className="micro">Eyebrow 11/14 · 600 · +0.06em</code>
          <Eyebrow>Financial health score</Eyebrow>
        </div>
        <div>
          <code className="micro">Figures · tabular</code>
          <span className="num fig">$150,000 · $18,000 · 18%</span>
        </div>
      </div>
    </section>
  )
}
