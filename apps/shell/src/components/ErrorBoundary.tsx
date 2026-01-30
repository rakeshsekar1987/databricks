import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  moduleName?: string;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Production-ready Error Boundary
 * Catches JavaScript errors in child component tree and displays fallback UI
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });

    // Log error
    console.error('[ErrorBoundary] Caught error:', {
      moduleName: this.props.moduleName,
      error: error.message,
      componentStack: errorInfo.componentStack,
    });

    // Call error callback if provided
    this.props.onError?.(error, errorInfo);

    // In production, send to error tracking service
    if (process.env.NODE_ENV === 'production') {
      this.reportError(error, errorInfo);
    }
  }

  private reportError(error: Error, errorInfo: ErrorInfo) {
    // Integration point for error tracking (Sentry, etc.)
    try {
      // Example: Send to error tracking API
      const errorData = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        moduleName: this.props.moduleName,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        userAgent: navigator.userAgent,
      };

      // navigator.sendBeacon('/api/errors', JSON.stringify(errorData));
      console.error('[ErrorBoundary] Error reported:', errorData);
    } catch (e) {
      console.error('[ErrorBoundary] Failed to report error:', e);
    }
  }

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback, moduleName } = this.props;

    if (hasError) {
      if (fallback) {
        return fallback;
      }

      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <div className="error-icon">❌</div>
            <h2>Something went wrong</h2>
            {moduleName && (
              <p className="error-module">
                Module: <strong>{moduleName}</strong>
              </p>
            )}
            <p className="error-message">
              {error?.message || 'An unexpected error occurred'}
            </p>
            <div className="error-actions">
              <button onClick={this.handleRetry} className="btn btn-primary">
                🔄 Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="btn btn-secondary"
              >
                ↻ Reload Page
              </button>
            </div>
            {process.env.NODE_ENV === 'development' && errorInfo && (
              <details className="error-details">
                <summary>Technical Details</summary>
                <div className="error-stack">
                  <h4>Error Stack:</h4>
                  <pre>{error?.stack}</pre>
                </div>
                <div className="error-component-stack">
                  <h4>Component Stack:</h4>
                  <pre>{errorInfo.componentStack}</pre>
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    return children;
  }
}

export default ErrorBoundary;
