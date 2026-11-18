import { useState } from 'react'
import { AppShell } from './AppShell'
import { ErrorBoundary } from './ErrorBoundary'
import { FamilyProvider } from '../features/family/state/FamilyProvider'
import { MentorProvider } from '../features/family/state/MentorProvider'
import type { PrototypeMode } from '../features/family/types'

/**
 * Root of the prototype.
 *
 * The shell's mode (family app vs. design system) is the only piece of state
 * that lives above the family feature; everything else belongs to the family
 * provider.
 */
export default function App() {
  const [mode, setMode] = useState<PrototypeMode>('family')

  return (
    <ErrorBoundary>
      <FamilyProvider>
        <MentorProvider>
          <AppShell mode={mode} onModeChange={setMode} />
        </MentorProvider>
      </FamilyProvider>
    </ErrorBoundary>
  )
}
