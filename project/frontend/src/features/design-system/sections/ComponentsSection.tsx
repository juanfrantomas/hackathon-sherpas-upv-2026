import { Button } from '../../../components/ui/Button'
import { Card } from '../../../components/ui/Card'
import { Chip } from '../../../components/ui/Chip'
import { DemoTag } from '../../../components/ui/DemoTag'
import { Eyebrow } from '../../../components/ui/Eyebrow'
import { Icon } from '../../../components/ui/Icon'
import { SegmentedControl } from '../../../components/ui/SegmentedControl'
import { StatusIcon } from '../../../components/ui/StatusIcon'
import { Toggle } from '../../../components/ui/Toggle'
import { MILESTONE_STATUSES } from '../../../components/ui/statusMeta'
import type { MilestoneStatus } from '../../family/types'

/** Buttons, cards, status, inputs and navigation. */
export function ComponentsSection() {
  return (
    <>
      <section className="ds-sec">
        <h2 className="h3">Buttons</h2>
        <div className="ds-row">
          <Button>Explore my financial plan</Button>
          <Button variant="secondary">Open in plan</Button>
          <Button variant="ghost" icon="mic">
            Ask the mentor
          </Button>
          <Button disabled>Disabled</Button>
          <Button size="sm" variant="secondary">
            Small
          </Button>
        </div>
      </section>

      <section className="ds-sec ds-two">
        <div className="stack-3">
          <h2 className="h3">Cards and status</h2>
          <Card className="next-step" tone="accent">
            <Eyebrow>Your next step</Eyebrow>
            <h3>Understand your credit card debt</h3>
            <p className="small">
              Primary recommendation card. Soft blue gradient, no shadow.
            </p>
          </Card>
          <Card>
            <Eyebrow>Default card</Eyebrow>
            <p className="small">White surface, 1px line, radius 16.</p>
          </Card>
          <div className="ds-row">
            <Chip tone="neutral">Not started</Chip>
            <Chip tone="blue">In progress</Chip>
            <Chip tone="ok">Completed</Chip>
            <Chip tone="warn">Needs review</Chip>
            <DemoTag />
          </div>
          <div className="ds-row">
            {MILESTONE_STATUSES.map((status) => (
              <StatusIcon key={status} status={status as MilestoneStatus} />
            ))}
          </div>
        </div>

        <div className="stack-3">
          <h2 className="h3">Inputs and navigation</h2>
          <label className="field" htmlFor="ds-in">
            <span className="field__label">Anything you'd like to add?</span>
            <textarea id="ds-in" rows={2} placeholder="A sentence is enough." />
          </label>
          <Toggle
            id="ds-t"
            checked
            onChange={() => {}}
            label="Share this update with my advisor"
          />
          <SegmentedControl
            value="a"
            onChange={() => {}}
            options={[
              { value: 'a', label: 'Milestones' },
              { value: 'b', label: 'Journey' },
            ]}
          />
          <div className="ds-row">
            <button className="pill is-on">Debt management</button>
            <button className="pill">Savings &amp; Expenses</button>
          </div>
          <div className="tabbar tabbar--demo">
            <span className="tabbar__item is-on">
              <Icon name="home" size={22} />
              <span>Home</span>
            </span>
            <span className="tabbar__item">
              <Icon name="plan" size={22} />
              <span>My Plan</span>
            </span>
            <span className="tabbar__item">
              <Icon name="progress" size={22} />
              <span>Progress</span>
            </span>
            <span className="tabbar__item tabbar__mentor">
              <span className="tabbar__mic">
                <Icon name="mic" size={20} />
              </span>
              <span>Mentor</span>
            </span>
          </div>
        </div>
      </section>
    </>
  )
}
