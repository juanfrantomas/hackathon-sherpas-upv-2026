/**
 * Two bars on one scale: cash against the credit card balance.
 * Only figures taken from the Sherpas plan are plotted — no projections.
 */
export function CashDebtBars() {
  const bars = [
    { label: 'Cash', value: 150000, text: '$150,000', cls: 'bar--cash' },
    {
      label: 'Credit card debt · 18%',
      value: 18000,
      text: '$18,000',
      cls: 'bar--debt',
    },
  ]

  return (
    <figure className="chart">
      <div className="bars">
        {bars.map((bar) => (
          <div className="bars__row" key={bar.label}>
            <div className="bars__meta">
              <span>{bar.label}</span>
              <strong className="num">{bar.text}</strong>
            </div>
            <div className="bars__track">
              <div
                className={`bars__fill ${bar.cls}`}
                style={{ width: `${(bar.value / 150000) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      <figcaption>Same scale. Figures from your Sherpas plan.</figcaption>
    </figure>
  )
}
