import type { CSSProperties } from 'react'
import { Icon } from '../../../components/ui/Icon'
import type { VoiceState } from '../types'

/** The animated orb that shows what the mentor is doing. */
export function VoiceOrb({ state }: { state: VoiceState }) {
  return (
    <div className={`orb orb--${state}`} aria-hidden="true">
      <div className="orb__halo" />
      <div className="orb__ring" />
      <div className="orb__core">
        {state === 'thinking' ? (
          <div className="orb__dots">
            <span />
            <span />
            <span />
          </div>
        ) : state === 'muted' ? (
          <Icon name="micOff" size={34} />
        ) : state === 'error' ? (
          <Icon name="wifiOff" size={34} />
        ) : (
          <div className="wave">
            {Array.from({ length: 21 }).map((_, index) => (
              <span
                key={index}
                style={
                  {
                    animationDelay: `${(index * 97) % 900}ms`,
                    '--h': `${0.35 + 0.65 * Math.abs(Math.sin(index * 0.7 + 0.3))}`,
                  } as CSSProperties
                }
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
