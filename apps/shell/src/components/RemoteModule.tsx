import React, { Suspense, useState, useEffect, useCallback } from 'react';
import { loadRemoteModule, RemoteModuleConfig } from '@/lib/moduleFederation';
import { RemoteConfig, toModuleConfig } from '@/lib/remoteConfig';
import ErrorBoundary from './ErrorBoundary';
import LoadingSpinner from './LoadingSpinner';

interface RemoteModuleProps {
  remote: RemoteConfig;
  fallback?: React.ReactNode;
}

interface ModuleState {
  Component: React.ComponentType | null;
  loading: boolean;
  error: Error | null;
  loadTime: number | null;
}

/**
 * RemoteModule - Production-ready component for loading federated modules
 * Features:
 * - Dynamic loading with error handling
 * - Retry capability
 * - Performance tracking
 * - Graceful degradation
 */
const RemoteModule: React.FC<RemoteModuleProps> = ({ remote, fallback }) => {
  const [state, setState] = useState<ModuleState>({
    Component: null,
    loading: true,
    error: null,
    loadTime: null,
  });

  const [retryCount, setRetryCount] = useState(0);

  const loadModule = useCallback(async () => {
    const startTime = performance.now();
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const config: RemoteModuleConfig = toModuleConfig(remote);
      const Component = await loadRemoteModule<React.ComponentType>(config);
      
      const loadTime = Math.round(performance.now() - startTime);
      
      setState({
        Component,
        loading: false,
        error: null,
        loadTime,
      });

      // Log performance metrics
      if (process.env.NODE_ENV === 'development') {
        console.info(`[RemoteModule] ${remote.displayName} loaded in ${loadTime}ms`);
      }
    } catch (error) {
      console.error(`[RemoteModule] Failed to load ${remote.displayName}:`, error);
      setState({
        Component: null,
        loading: false,
        error: error as Error,
        loadTime: null,
      });
    }
  }, [remote]);

  useEffect(() => {
    loadModule();
  }, [loadModule, retryCount]);

  const handleRetry = () => {
    setRetryCount((prev) => prev + 1);
  };

  // Loading state
  if (state.loading) {
    return (
      <div className="remote-module-container">
        <ModuleHeader remote={remote} loadTime={null} />
        <div className="remote-module-content">
          {fallback || <LoadingSpinner message={`Loading ${remote.displayName}...`} />}
        </div>
      </div>
    );
  }

  // Error state
  if (state.error) {
    return (
      <div className="remote-module-container">
        <ModuleHeader remote={remote} loadTime={null} />
        <div className="remote-module-content">
          <ModuleErrorFallback
            moduleName={remote.displayName}
            error={state.error}
            onRetry={handleRetry}
          />
        </div>
      </div>
    );
  }

  // Success state
  const { Component } = state;
  if (!Component) {
    return null;
  }

  return (
    <div className="remote-module-container">
      <ModuleHeader remote={remote} loadTime={state.loadTime} />
      <div className="remote-module-content">
        <ErrorBoundary
          moduleName={remote.displayName}
          onError={(error) => {
            console.error(`[RemoteModule] Runtime error in ${remote.displayName}:`, error);
          }}
        >
          <Suspense fallback={<LoadingSpinner message="Loading..." />}>
            <Component />
          </Suspense>
        </ErrorBoundary>
      </div>
    </div>
  );
};

// Module Header Component
interface ModuleHeaderProps {
  remote: RemoteConfig;
  loadTime: number | null;
}

const ModuleHeader: React.FC<ModuleHeaderProps> = ({ remote, loadTime }) => (
  <div className="module-header">
    <div className="module-header-left">
      <span className="module-icon">{remote.icon}</span>
      <h2 className="module-title">{remote.displayName}</h2>
    </div>
    <div className="module-header-right">
      {remote.agGridVersion && (
        <span className="ag-grid-badge">AG Grid v{remote.agGridVersion}</span>
      )}
      {loadTime !== null && (
        <span className="load-time-badge">Loaded in {loadTime}ms</span>
      )}
    </div>
  </div>
);

// Error Fallback Component
interface ModuleErrorFallbackProps {
  moduleName: string;
  error: Error;
  onRetry: () => void;
}

const ModuleErrorFallback: React.FC<ModuleErrorFallbackProps> = ({
  moduleName,
  error,
  onRetry,
}) => (
  <div className="module-error">
    <div className="module-error-icon">⚠️</div>
    <h3>Failed to Load Module</h3>
    <p className="module-error-name">{moduleName}</p>
    <p className="module-error-message">{error.message}</p>
    <div className="module-error-actions">
      <button onClick={onRetry} className="btn btn-primary">
        🔄 Retry
      </button>
      <button onClick={() => window.location.reload()} className="btn btn-secondary">
        ↻ Reload Page
      </button>
    </div>
    {process.env.NODE_ENV === 'development' && (
      <details className="module-error-details">
        <summary>Error Details</summary>
        <pre>{error.stack}</pre>
      </details>
    )}
  </div>
);

export default RemoteModule;
