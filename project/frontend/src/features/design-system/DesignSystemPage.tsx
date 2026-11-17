import { Eyebrow } from '../../components/ui/Eyebrow'
import { Icon } from '../../components/ui/Icon'
import { Wordmark } from '../../components/brand/Wordmark'
import { ApproxBadge } from './ApproxBadge'
import { ColorSection } from './sections/ColorSection'
import { ComponentsSection } from './sections/ComponentsSection'
import { DataSection } from './sections/DataSection'
import { LayoutSection } from './sections/LayoutSection'
import { TypographySection } from './sections/TypographySection'

/** The design-system reference page of the prototype. */
export function DesignSystemPage() {
  return (
    <div className="ds">
      <section className="ds-intro">
        <Eyebrow>MySherpas · design system v0.1</Eyebrow>
        <h1 className="h-display">Built on the Sherpas Wealth language</h1>
        <p className="muted">
          White and light-gray surfaces, one blue accent, charcoal type, thin borders,
          almost no shadow. Health score and plan sections follow the existing Sherpas
          plan: the score shown as a number out of 100 with the rules-based disclaimer,
          and sections named Retirement &amp; Goals, Assets &amp; Investments, Debt
          management, Savings &amp; Expenses, and Insurance &amp; Protection.
        </p>
        <div className="callout callout--warn">
          <Icon name="info" size={20} />
          <div>
            <strong>Reference status</strong>
            <p className="small">
              From here I could read sherpaswealth.com's copy and navigation and the
              shared plan's structure and wording. The product screenshots, the site's
              CSS and the logo file could not be downloaded. Every value marked{' '}
              <ApproxBadge /> is an approximation to replace with official tokens. The
              mark below is a placeholder, not the Sherpas logo.
            </p>
          </div>
        </div>
      </section>

      <section className="ds-sec">
        <h2 className="h3">Brand</h2>
        <div className="ds-row">
          <Wordmark size="lg" />
          <Wordmark size="md" product={false} />
          <span className="small muted">
            Logo placeholder <ApproxBadge />
          </span>
        </div>
      </section>

      <ColorSection />
      <TypographySection />
      <LayoutSection />
      <ComponentsSection />
      <DataSection />
    </div>
  )
}
