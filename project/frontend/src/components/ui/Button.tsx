import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Icon } from './Icon'
import type { IconName } from './iconPaths'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  icon?: IconName
  iconRight?: IconName
  block?: boolean
  children?: ReactNode
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  iconRight,
  block = false,
  children,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`btn btn--${variant} btn--${size}${block ? ' btn--block' : ''}`}
      {...rest}
    >
      {icon && <Icon name={icon} size={18} />}
      {children && <span>{children}</span>}
      {iconRight && <Icon name={iconRight} size={18} />}
    </button>
  )
}
