import type { ReactNode } from 'react'
import { Icon } from '../../../components/ui/Icon'

export interface ScreenHeaderProps {
  title: string
  onBack?: () => void
  right?: ReactNode
}

/** Sticky top bar of a phone screen: optional back button, title, optional action. */
export function ScreenHeader({ title, onBack, right }: ScreenHeaderProps) {
  return (
    <header className="topbar">
      {onBack ? (
        <button className="icon-btn" onClick={onBack} aria-label="Back">
          <Icon name="chevronLeft" size={22} />
        </button>
      ) : (
        <span className="icon-btn-sp" />
      )}
      <h1 className="topbar__title">{title}</h1>
      {right || <span className="icon-btn-sp" />}
    </header>
  )
}
