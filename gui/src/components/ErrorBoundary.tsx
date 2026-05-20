import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
  errorInfo: ErrorInfo | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ error, errorInfo })
  }

  handleDismiss = (): void => {
    this.setState({ error: null, errorInfo: null })
  }

  render(): ReactNode {
    if (this.state.error !== null) {
      const msg = this.state.error.message || 'An unexpected error occurred'
      const truncated = msg.length > 200 ? msg.slice(0, 200) + '…' : msg
      return (
        <div
          className="flex min-h-[200px] flex-col items-center justify-center gap-4 rounded border border-red-700 bg-red-900/20 p-6"
          data-testid="error-boundary-fallback"
          role="alert"
        >
          <p className="text-center text-sm text-red-400" data-testid="error-boundary-message">
            {truncated}
          </p>
          <button
            type="button"
            onClick={this.handleDismiss}
            className="rounded border border-gray-600 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700"
            data-testid="error-boundary-dismiss"
          >
            Go Back
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
