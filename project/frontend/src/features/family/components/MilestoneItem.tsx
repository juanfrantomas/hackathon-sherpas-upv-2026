import { Button } from '../../../components/ui/Button'
import { Chip } from '../../../components/ui/Chip'
import { Icon } from '../../../components/ui/Icon'
import { StatusIcon } from '../../../components/ui/StatusIcon'
import { MILESTONE_STATUSES, STATUS_META } from '../../../components/ui/statusMeta'
import type { MilestoneStatus, Navigate } from '../types'
import type { MilestoneWithStatus } from '../state/selectors'

export interface MilestoneItemProps {
  milestone: MilestoneWithStatus
  open: boolean
  /** True for the last item in the list, which has no connecting rail. */
  last: boolean
  /** True right after the household marked it complete. */
  justDone: boolean
  onToggle: () => void
  setStatus: (milestoneId: string, status: MilestoneStatus) => void
  go: Navigate
}

/** One milestone on the progress timeline. */
export function MilestoneItem({
  milestone,
  open,
  last,
  justDone,
  onToggle,
  setStatus,
  go,
}: MilestoneItemProps) {
  const meta = STATUS_META[milestone.status]

  return (
    <li className={`ms ms--${milestone.status}${open ? ' is-open' : ''}`}>
      <div className="ms__rail">
        <StatusIcon status={milestone.status} />
        {!last && <span className="ms__line" />}
      </div>

      <div className="ms__card">
        <button className="ms__head" onClick={onToggle} aria-expanded={open}>
          <div className="grow">
            <strong>{milestone.title}</strong>
            <div className="ms__meta">
              <Chip tone={meta.tone}>{meta.label}</Chip>
              {milestone.overdue && milestone.status !== 'completed' && (
                <Chip tone="warn">Overdue</Chip>
              )}
              {milestone.taskProgress != null && (
                <span className="micro muted">{Math.round(milestone.taskProgress)}% of tasks</span>
              )}
              {milestone.checkin && milestone.status !== 'completed' && (
                <span className="micro muted">Check-in {milestone.checkin}</span>
              )}
            </div>
          </div>
          <Icon name="chevronDown" size={18} className="rec__chev" />
        </button>

        {justDone && (
          <div className="ms__praise">
            <Icon name="check" size={16} stroke={2.2} />
            {' Nice work. That\'s one step clearer.'}
          </div>
        )}

        {open && (
          <div className="ms__body">
            <p className="small">
              <span className="muted">Why it matters. </span>
              {milestone.why}
            </p>
            <p className="small">
              <span className="muted">Next action. </span>
              {milestone.action}
            </p>

            <div className="row-wrap">
              <Button
                size="sm"
                variant="secondary"
                iconRight="arrowRight"
                onClick={() => go('plan', { section: milestone.section })}
              >
                Open in plan
              </Button>
              <Button
                size="sm"
                variant="ghost"
                icon="mic"
                onClick={() => go('mentor', { from: 'progress', topic: milestone.title })}
              >
                Ask
              </Button>
            </div>

            <div className="ms__set">
              <span className="micro muted">Update status</span>
              <div className="seg seg--sm">
                {MILESTONE_STATUSES.map((status) => (
                  <button
                    key={status}
                    className={milestone.status === status ? 'is-on' : ''}
                    onClick={() => setStatus(milestone.id, status)}
                  >
                    {STATUS_META[status].label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </li>
  )
}
