import React, { Suspense, useState, useEffect } from 'react';
import ErrorBoundary from './ErrorBoundary';
import LoadingSpinner from './LoadingSpinner';

interface ModuleLoaderProps {
  children: React.ReactNode;
  moduleName: string;
  fallback?: React.ReactNode;
}

/**
 * ModuleLoader wraps remote federated modules with:
 * - Error boundary for graceful error handling
 * - Loading state with spinner
 * - Module availability tracking
 */
const ModuleLoader: React.FC<ModuleLoaderProps> = ({
  children,
  moduleName,
  fallback,
}) => {
  const [loadStartTime] = useState(Date.now());
  const [loadTime, setLoadTime] = useState<number | null>(null);

  useEffect(() => {
    // Track when the module finishes loading
    if (loadTime === null) {
      const timer = setTimeout(() => {
        setLoadTime(Date.now() - loadStartTime);
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [loadStartTime, loadTime]);

  return (
    <div className="module-container" data-module={moduleName}>
      <ErrorBoundary moduleName={moduleName}>
        <Suspense
          fallback={
            fallback || (
              <LoadingSpinner message={`Loading ${moduleName}...`} />
            )
          }
        >
          <div className="module-header">
            <h2 className="module-title">{moduleName}</h2>
            {loadTime && (
              <span className="module-load-time">
                Loaded in {loadTime}ms
              </span>
            )}
          </div>
          <div className="module-content">
            {children}
          </div>
        </Suspense>
      </ErrorBoundary>
    </div>
  );
};

export default ModuleLoader;
