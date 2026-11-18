export interface ColorSwatchProps {
  /** Human-readable token name. */
  name: string
  /** CSS custom property, e.g. `--sw-blue-600`. */
  variable: string
  /** Hex value, e.g. `#2a56d8`. */
  hex: string
}

/** One colour token: a chip, its name and its value. */
export function ColorSwatch({ name, variable, hex }: ColorSwatchProps) {
  return (
    <div className="sw">
      <span className="sw__chip" style={{ background: `var(${variable})` }} />
      <div>
        <strong className="small">{name}</strong>
        <code className="micro">
          {variable} · {hex}
        </code>
      </div>
    </div>
  )
}
