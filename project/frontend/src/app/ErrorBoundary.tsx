import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Button } from '../components/ui/Button'
import { Icon } from '../components/ui/Icon'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

/**
 * Keeps a render error from blanking the whole prototype.
 * Purely additive: the happy path renders exactly as before.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('MySherpas render error', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="pad stack-3">
          <div className="callout callout--err">
            <Icon name="info" size={20} />
            <div>
              <strong>Something went wrong while drawing this screen.</strong>
              <p className="small">{this.state.error.message}</p>
            </div>
          </div>
          <Button onClick={() => this.setState({ error: null })}>Try again</Button>
        </div>
      )
    }
    return this.props.children
  }
}
