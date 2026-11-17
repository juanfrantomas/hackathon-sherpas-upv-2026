import type { CSSProperties } from 'react'
import { ICON_PATHS, type IconName } from './iconPaths'

export interface IconProps {
  name: IconName
  size?: number
  stroke?: number
  className?: string
  style?: CSSProperties
}

/** Decorative inline SVG icon. Always hidden from assistive technology. */
export function Icon({
  name,
  size = 20,
  stroke = 1.6,
  className = '',
  style,
}: IconProps) {
  return (
    <svg
      className={className ? `ic ${className}` : 'ic'}
      style={style}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={ICON_PATHS[name]} />
    </svg>
  )
}
