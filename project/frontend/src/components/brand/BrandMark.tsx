/**
 * Placeholder brand mark.
 *
 * The prototype's own documentation states the real Sherpas logo could not be
 * downloaded, so this geometric placeholder is reproduced on purpose.
 */
export function BrandMark({ size = 22 }: { size?: number }) {
  return (
    <span className="brand-mark" style={{ width: size, height: size }} aria-hidden="true">
      <svg viewBox="0 0 24 24" width={size * 0.62} height={size * 0.62}>
        <path d="M3 19 10 7l3.5 6 2-3L21 19z" fill="currentColor" />
      </svg>
    </span>
  )
}
