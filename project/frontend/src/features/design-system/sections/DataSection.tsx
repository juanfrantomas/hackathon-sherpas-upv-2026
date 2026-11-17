import { Card } from '../../../components/ui/Card'
import { ScoreRing } from '../../../components/ui/ScoreRing'
import { CashDebtBars } from '../../../components/charts/CashDebtBars'
import { GoalTimeline } from '../../../components/charts/GoalTimeline'

const VOICE_STATE_SAMPLES: Array<[string, string, string]> = [
  ['ready', 'Ready', 'Still ring, soft halo'],
  ['listening', 'Listening', 'Bars follow your voice'],
  ['thinking', 'Thinking', 'Slow pulse, three dots'],
  ['speaking', 'Speaking', 'Blue bars, interrupt hint'],
  ['interrupted', 'Interrupted', 'Mentor line cut, you speak'],
  ['muted', 'Muted', 'Gray, mic-off glyph'],
  ['error', 'Unavailable', 'Retry, or read the plan'],
]

/** The financial charts and the voice-interaction states. */
export function DataSection() {
  return (
    <section className="ds-sec ds-two">
      <div className="stack-3">
        <h2 className="h3">Financial charts</h2>
        <p className="small muted">
          One blue, one neutral, shared scale, figures labeled directly. Only plan
          values are plotted. No projections.
        </p>
        <Card>
          <CashDebtBars />
        </Card>
        <Card>
          <GoalTimeline
            caption="Dates and ages exactly as stated in the plan."
            points={[
              { k: 'Today', v: 'Score 26', now: true },
              { k: '2027', v: '$550,000 home' },
              { k: 'Age 58', v: 'Retire' },
            ]}
          />
        </Card>
        <div className="ds-row">
          <ScoreRing score={60} />
          <ScoreRing score={82} size={72} stroke={6} />
        </div>
      </div>

      <div className="stack-3">
        <h2 className="h3">Voice interaction states</h2>
        <div className="voice-states">
          {VOICE_STATE_SAMPLES.map(([state, label, note]) => (
            <div key={state} className={`vs vs--${state}`}>
              <span className="vs__dot" />
              <div>
                <strong className="small">{label}</strong>
                <span className="micro muted">{note}</span>
              </div>
            </div>
          ))}
        </div>
        <p className="small muted">
          See them live in the family app: open the Mentor and use the state controls
          beside the phone.
        </p>
      </div>
    </section>
  )
}
