import { Icon } from '../../../components/ui/Icon'
import type { IconName } from '../../../components/ui/iconPaths'
import type { FamilyScreen, NavigateOptions } from '../types'

const TAB_ITEMS: ReadonlyArray<{ id: FamilyScreen; label: string; icon: IconName }> = [
  { id: 'home', label: 'Home', icon: 'home' },
  { id: 'plan', label: 'My Plan', icon: 'plan' },
  { id: 'progress', label: 'Progress', icon: 'progress' },
]

export interface TabBarProps {
  active: FamilyScreen
  go: (screen: FamilyScreen, options?: NavigateOptions) => void
}

/** Bottom navigation of the family app. */
export function TabBar({ active, go }: TabBarProps) {
  return (
    <nav className="tabbar" aria-label="Main">
      {TAB_ITEMS.map((item) => (
        <button
          key={item.id}
          className={`tabbar__item${active === item.id ? ' is-on' : ''}`}
          onClick={() => go(item.id)}
          aria-current={active === item.id ? 'page' : undefined}
        >
          <Icon name={item.icon} size={22} />
          <span>{item.label}</span>
        </button>
      ))}
      <button
        className="tabbar__item tabbar__mentor"
        onClick={() => go('mentor', { from: active })}
      >
        <span className="tabbar__mic">
          <Icon name="mic" size={20} stroke={1.8} />
        </span>
        <span>Mentor</span>
      </button>
    </nav>
  )
}
