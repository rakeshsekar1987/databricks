import React, { Suspense, useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import RemoteModule from './components/RemoteModule';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';
import { getRemoteConfigs, RemoteConfig } from './lib/remoteConfig';
import { preloadRemoteModule } from './lib/moduleFederation';
import HomePage from './pages/HomePage';

/**
 * Main Application Component
 * Manages routing and remote module loading
 */
const App: React.FC = () => {
  const [remotes] = useState<Record<string, RemoteConfig>>(getRemoteConfigs());
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize and preload critical modules
  useEffect(() => {
    const init = async () => {
      try {
        // Preload remote entry scripts for faster navigation
        if (process.env.ENABLE_MODULE_PRELOADING === 'true') {
          Object.values(remotes).forEach((remote) => {
            preloadRemoteModule(remote.url);
          });
        }
      } catch (error) {
        console.error('[App] Initialization error:', error);
      } finally {
        setIsInitialized(true);
      }
    };

    init();
  }, [remotes]);

  if (!isInitialized) {
    return <LoadingSpinner message="Initializing application..." fullScreen />;
  }

  return (
    <ErrorBoundary moduleName="Shell">
      <Layout>
        <Suspense fallback={<LoadingSpinner message="Loading page..." />}>
          <Routes>
            {/* Home Page */}
            <Route path="/" element={<HomePage remotes={remotes} />} />

            {/* Dynamic routes for each remote module */}
            <Route
              path="/reg-reporting/*"
              element={<RemoteModule remote={remotes.regReporting} />}
            />
            <Route
              path="/financial-reporting/*"
              element={<RemoteModule remote={remotes.financialReporting} />}
            />
            <Route
              path="/expense-reporting/*"
              element={<RemoteModule remote={remotes.expenseReporting} />}
            />
            <Route
              path="/tax-reporting/*"
              element={<RemoteModule remote={remotes.taxReporting} />}
            />
            <Route
              path="/control-tower/*"
              element={<RemoteModule remote={remotes.controlTower} />}
            />

            {/* 404 Redirect */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </Layout>
    </ErrorBoundary>
  );
};

export default App;
