export interface TimelinePoint {
  /** Point label, e.g. "2027". */
  k: string
  /** Value label, e.g. "$550,000 home". */
  v: string
  /** Marks the point as "now". */
  now?: boolean
}

export interface GoalTimelineProps {
  points: TimelinePoint[]
  caption: string
}

/** Three-point timeline across a household's goals. */
export function GoalTimeline({ points, caption }: GoalTimelineProps) {
  return (
    <figure className="chart">
      <div className="gtl">
        <div className="gtl__line" />
        {points.map((point, index) => (
          <div
            key={point.k}
            className={`gtl__pt${point.now ? ' is-now' : ''}`}
            style={{ left: `${(index / (points.length - 1)) * 100}%` }}
          >
            <span className="gtl__dot" />
            <span className="gtl__k">{point.k}</span>
            <span className="gtl__v">{point.v}</span>
          </div>
        ))}
      </div>
      <figcaption>{caption}</figcaption>
    </figure>
  )
}
