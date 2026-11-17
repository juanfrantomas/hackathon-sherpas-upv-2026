const SPACING_SCALE = [4, 8, 12, 16, 20, 24, 32, 40]

const RADII: Array<[string, number]> = [
  ['sm', 8],
  ['md', 12],
  ['lg', 16],
  ['xl', 24],
]

const SHADOWS = ['--sh-1', '--sh-2', '--sh-3']

/** The spacing scale, the corner radii and the elevation scale. */
export function LayoutSection() {
  return (
    <section className="ds-sec ds-two">
      <div>
        <h2 className="h3">Spacing · 4px base</h2>
        <div className="space-scale">
          {SPACING_SCALE.map((size) => (
            <div key={size}>
              <span style={{ width: size, height: size }} />
              <code className="micro">{size}</code>
            </div>
          ))}
        </div>
      </div>
      <div>
        <h2 className="h3">Radii and elevation</h2>
        <div className="ds-row">
          {RADII.map(([name, radius]) => (
            <div key={name} className="radius-demo" style={{ borderRadius: radius }}>
              <code className="micro">
                {name} · {radius}
              </code>
            </div>
          ))}
        </div>
        <div className="ds-row">
          {SHADOWS.map((shadow) => (
            <div
              key={shadow}
              className="shadow-demo"
              style={{ boxShadow: `var(${shadow})` }}
            >
              <code className="micro">{shadow}</code>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
