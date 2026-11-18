export interface ToggleProps {
  id: string
  checked: boolean
  onChange: (checked: boolean) => void
  label: string
}

/** Checkbox rendered as a switch. */
export function Toggle({ id, checked, onChange, label }: ToggleProps) {
  return (
    <label className="toggle" htmlFor={id}>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="toggle__track">
        <span className="toggle__thumb" />
      </span>
      <span className="toggle__label">{label}</span>
    </label>
  )
}
