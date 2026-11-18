import type { ReactNode } from 'react'

export interface DemoTagProps {
  children?: ReactNode
}

/** Marks content as sample data rather than verified financial activity. */
export function DemoTag({ children = 'Demo' }: DemoTagProps) {
  return (
    <span
      className="demo-tag"
      title="Sample content for the prototype. Not verified financial activity."
    >
      {children}
    </span>
  )
}
