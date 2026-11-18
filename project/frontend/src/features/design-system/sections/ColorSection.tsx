import { ColorSwatch } from '../ColorSwatch'
import { ApproxBadge } from '../ApproxBadge'

const BRAND_COLORS: Array<[string, string, string]> = [
  ['Brand blue 700', '--sw-blue-700', '#1f45b8'],
  ['Brand blue 600 · primary', '--sw-blue-600', '#2a56d8'],
  ['Brand blue 500', '--sw-blue-500', '#4a72e6'],
  ['Blue 200', '--sw-blue-200', '#c9d7fb'],
  ['Blue 100', '--sw-blue-100', '#e3ebfd'],
  ['Blue 50', '--sw-blue-50', '#f2f6ff'],
]

const NEUTRAL_COLORS: Array<[string, string, string]> = [
  ['Ink 900 · text', '--ink-900', '#1c2230'],
  ['Ink 700', '--ink-700', '#3a4252'],
  ['Ink 500 · secondary', '--ink-500', '#5f6878'],
  ['Ink 400', '--ink-400', '#8a92a1'],
  ['Line', '--line', '#e5e8ee'],
  ['Canvas', '--canvas', '#f6f7fa'],
  ['Surface', '--surface', '#ffffff'],
]

const SEMANTIC_COLORS: Array<[string, string, string]> = [
  ['OK 600', '--ok-600', '#17845a'],
  ['Warn 600', '--warn-600', '#a46a12'],
  ['Error 600', '--err-600', '#b4433b'],
]

/** The colour tokens, and the two surface gradients. */
export function ColorSection() {
  return (
    <section className="ds-sec">
      <h2 className="h3">
        Color <ApproxBadge />
      </h2>
      <div className="sw-grid">
        {BRAND_COLORS.map(([name, variable, hex]) => (
          <ColorSwatch key={variable} name={name} variable={variable} hex={hex} />
        ))}
      </div>
      <div className="sw-grid">
        {NEUTRAL_COLORS.map(([name, variable, hex]) => (
          <ColorSwatch key={variable} name={name} variable={variable} hex={hex} />
        ))}
      </div>
      <div className="sw-grid">
        {SEMANTIC_COLORS.map(([name, variable, hex]) => (
          <ColorSwatch key={variable} name={name} variable={variable} hex={hex} />
        ))}
      </div>
      <div className="ds-row">
        <div
          className="grad-sample"
          style={{ background: 'var(--sw-gradient-soft)' }}
        >
          Soft surface gradient
        </div>
        <div
          className="grad-sample grad-sample--accent"
          style={{ background: 'var(--sw-gradient-accent)' }}
        >
          Accent gradient, sparingly
        </div>
      </div>
      <p className="small muted">
        Semantic colors are for state only. Warn means "worth a look",
        never a penalty.
      </p>
    </section>
  )
}
