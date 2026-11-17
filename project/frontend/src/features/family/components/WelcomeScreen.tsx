import { Button } from '../../../components/ui/Button'
import { Icon } from '../../../components/ui/Icon'
import { Wordmark } from '../../../components/brand/Wordmark'
import type { Family, Navigate } from '../types'

/** The shared plan the household can open in a new tab. */
export const DEFAULT_PLAN_URL =
  'https://app.sherpaswealth.com/plan/shared/RcCtgoNkGmD6dvGtYVKWLGefdCTFdc4JP_jH9Jbz2jo'

export interface WelcomeScreenProps {
  family: Family
  go: Navigate
}

/** Screen 1 — the household's first view of the app. */
export function WelcomeScreen({ family, go }: WelcomeScreenProps) {
  return (
    <div className="screen screen--welcome">
      <div className="welcome__top">
        <Wordmark size="md" />
      </div>

      <div className="welcome__body">
        <a
          className="welcome__badge"
          href={family.planUrl ?? DEFAULT_PLAN_URL}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Icon name="plan" size={16} />
          {' Based on your Sherpas financial plan (PDF report)'}
        </a>

        <h1 className="welcome__title">Welcome, {family.names}.</h1>
        <p className="welcome__lede">Your financial future, explained one step at a time.</p>
        <p className="welcome__copy">
          MySherpas turns your financial plan into something you can follow: a short
          story of where you stand, the next step that matters, and a mentor you can
          talk to whenever you have a question.
        </p>

        <ul className="welcome__list">
          <li>
            <Icon name="play" size={16} />
            {' A short story of your plan'}
          </li>
          <li>
            <Icon name="flag" size={16} />
            {' One clear next step at a time'}
          </li>
          <li>
            <Icon name="mic" size={16} />
            {' A voice mentor that knows your plan'}
          </li>
        </ul>
      </div>

      <div className="welcome__foot">
        <Button block size="lg" iconRight="arrowRight" onClick={() => go('story')}>
          Explore my financial plan
        </Button>
        <p className="fineprint">
          <Icon name="lock" size={13} />
          {' Private to your household. You choose what to share with an advisor.'}
        </p>
      </div>
    </div>
  )
}
