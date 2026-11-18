import type { ElementType, HTMLAttributes, ReactNode } from 'react'

export type CardTone = 'accent' | 'soft'

export interface CardProps extends HTMLAttributes<HTMLElement> {
  tone?: CardTone
  /** Element to render when the card is not interactive. */
  as?: ElementType
  onClick?: () => void
  children?: ReactNode
}

/**
 * Surface container. Renders as a `<button>` when it is interactive, which is
 * what the prototype did, so that the whole card is one keyboard-reachable
 * target.
 */
export function Card({
  children,
  className = '',
  tone,
  onClick,
  as: As = 'div',
  ...rest
}: CardProps) {
  const classes = [
    'card',
    tone ? `card--${tone}` : '',
    onClick ? 'card--tap' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  if (onClick) {
    return (
      <button type="button" className={classes} onClick={onClick} {...rest}>
        {children}
      </button>
    )
  }

  return (
    <As className={classes} {...rest}>
      {children}
    </As>
  )
}
