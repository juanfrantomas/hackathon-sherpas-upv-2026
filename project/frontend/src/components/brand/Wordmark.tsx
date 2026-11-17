import { BrandMark } from './BrandMark'

export type WordmarkSize = 'sm' | 'md' | 'lg'

export interface WordmarkProps {
  /** Renders the "My" prefix of the MySherpas product name. */
  product?: boolean
  size?: WordmarkSize
}

export function Wordmark({ product = true, size = 'md' }: WordmarkProps) {
  return (
    <span className={`wordmark wordmark--${size}`}>
      <BrandMark size={size === 'lg' ? 30 : 22} />
      <span>
        {product ? (
          <>
            <span className="wm-my">My</span>Sherpas
          </>
        ) : (
          'Sherpas'
        )}
      </span>
    </span>
  )
}
