/** Two goals that compete for the same money. */
export function TwoGoals() {
  return (
    <figure className="chart">
      <div className="two-goals">
        <div>
          <span className="tg__k">Goal</span>
          <strong>College funding</strong>
          <span className="tg__s">Two children</span>
        </div>
        <div className="tg__vs">or</div>
        <div>
          <span className="tg__k">Goal</span>
          <strong>Retirement</strong>
          <span className="tg__s">Your future</span>
        </div>
      </div>
      <figcaption>Both goals draw on the same money. Order is the decision.</figcaption>
    </figure>
  )
}
