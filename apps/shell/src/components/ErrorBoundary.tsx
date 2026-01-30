import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  moduleName?: string;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary for catching errors in federated modules
 * Provides graceful degradation when a module fails to load
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
    
    // Log error to monitoring service
    console.error('Module Error:', {
      moduleName: this.props.moduleName,
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
    });

    // In production, send to error tracking service
    // errorTrackingService.captureError(error, { moduleName: this.props.moduleName });
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary">
          <div className="error-content">
            <span className="error-icon">⚠️</span>
            <h2>Module Failed to Load</h2>
            {this.props.moduleName && (
              <p className="error-module">
                Module: <strong>{this.props.moduleName}</strong>
              </p>
            )}
            <p className="error-message">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <div className="error-actions">
              <button onClick={this.handleRetry} className="retry-button">
                🔄 Retry
              </button>
              <button
                onClick={() => window.location.reload()}
                className="reload-button"
              >
                ↻ Reload Page
              </button>
            </div>
            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <details className="error-details">
                <summary>Error Details</summary>
                <pre>{this.state.error?.stack}</pre>
                <pre>{this.state.errorInfo.componentStack}</pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
