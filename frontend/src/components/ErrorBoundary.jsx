import { Component } from 'react';

/**
 * Global error boundary that catches React rendering errors
 * and displays a recovery UI instead of a white screen.
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Allow custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-surface p-8">
          <div className="max-w-md w-full text-center space-y-6">
            <div className="text-6xl">⚠️</div>
            <h1 className="text-2xl font-bold text-text-primary">
              Something went wrong
            </h1>
            <p className="text-text-secondary">
              {this.props.message || 'An unexpected error occurred. Please try again.'}
            </p>
            {this.state.error && (
              <details className="text-left text-sm text-text-secondary bg-surface-secondary rounded-lg p-4">
                <summary className="cursor-pointer font-medium mb-2">Error Details</summary>
                <pre className="whitespace-pre-wrap break-words text-xs overflow-auto max-h-40">
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 
                         transition-colors font-medium"
              >
                Try Again
              </button>
              <button
                onClick={this.handleReload}
                className="px-4 py-2 bg-surface-secondary text-text-primary rounded-lg 
                         hover:bg-surface-secondary/80 transition-colors font-medium"
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Panel-level error boundary with minimal UI.
 * Wraps individual panels so one panel crashing doesn't break the whole app.
 */
export function PanelErrorBoundary({ children, panelName = 'Panel' }) {
  return (
    <ErrorBoundary
      message={`The ${panelName} encountered an error. Click "Try Again" to recover.`}
      fallback={null}
    >
      {children}
    </ErrorBoundary>
  );
}

export default ErrorBoundary;
