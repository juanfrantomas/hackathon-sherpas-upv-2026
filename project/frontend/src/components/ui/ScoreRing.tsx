export interface ScoreRingProps {
  score: number
  size?: number
  stroke?: number
  /** Shows the score and "/100" in the middle of the ring. */
  label?: boolean
}

/** Circular gauge showing a financial health score out of 100. */
export function ScoreRing({ score, size = 96, stroke = 8, label = true }: ScoreRingProps) {
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const track = circumference * 0.75
  const value = track * (score / 100)

  return (
    <div className="score-ring" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ transform: 'rotate(135deg)' }}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--sw-blue-100)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${track} ${circumference}`}
        />
        <circle
          className="score-ring__val"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--sw-blue-600)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${value} ${circumference}`}
        />
      </svg>
      {label && (
        <div className="score-ring__num num" style={{ fontSize: size * 0.3 }}>
          {score}
          <small>/100</small>
        </div>
      )}
    </div>
  )
}
