import type { ReactNode, RefObject } from 'react'
import type { FamilyScreen } from '../../types'
import { PhoneStatusBar } from './PhoneStatusBar'

export interface PhoneFrameProps {
  /** Current screen; also drives the status-bar tint. */
  screen: FamilyScreen
  /** Changes with the screen, to replay the enter animation. */
  screenKey: number
  /** Scroll container of the phone. */
  scrollRef: RefObject<HTMLDivElement | null>
  /** Bottom tab bar, shown only on some screens. */
  tabBar?: ReactNode
  children: ReactNode
}

/** The iPhone mockup the family app is shown inside. */
export function PhoneFrame({
  screen,
  screenKey,
  scrollRef,
  tabBar,
  children,
}: PhoneFrameProps) {
  return (
    <div className={`phone phone--tint-${screen}`}>
      <PhoneStatusBar />
      <div className="phone__screen" ref={scrollRef}>
        <div className="screen-anim" key={`${screen}-${screenKey}`}>
          {children}
        </div>
      </div>
      {tabBar}
      <div className="phone__home" />
    </div>
  )
}
