import React, { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ModuleLoader from './components/ModuleLoader';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';

// Dynamic imports for remote modules using Module Federation
// Each module is loaded from its remote entry point
const RegReporting = React.lazy(() => import('regReporting/App'));
const FinancialReporting = React.lazy(() => import('financialReporting/App'));
const ExpenseReporting = React.lazy(() => import('expenseReporting/App'));
const TaxReporting = React.lazy(() => import('taxReporting/App'));
const ControlTower = React.lazy(() => import('controlTower/App'));

// Home page component
const HomePage: React.FC = () => (
  <div className="home-page">
    <h1>UI Platform</h1>
    <p>Welcome to the Module Federation powered UI platform.</p>
    <div className="module-cards">
      <ModuleCard
        title="Regulatory Reporting"
        description="Manage regulatory compliance reports"
        path="/reg-reporting"
        icon="📋"
      />
      <ModuleCard
        title="Financial Reporting"
        description="Financial statements and analytics"
        path="/financial-reporting"
        icon="💰"
      />
      <ModuleCard
        title="Expense Reporting"
        description="Track and manage expenses"
        path="/expense-reporting"
        icon="💳"
      />
      <ModuleCard
        title="Tax Reporting"
        description="Tax calculations and filing"
        path="/tax-reporting"
        icon="📊"
      />
      <ModuleCard
        title="Control Tower"
        description="Dashboard and monitoring"
        path="/control-tower"
        icon="🎛️"
      />
    </div>
  </div>
);

interface ModuleCardProps {
  title: string;
  description: string;
  path: string;
  icon: string;
}

const ModuleCard: React.FC<ModuleCardProps> = ({ title, description, path, icon }) => (
  <a href={path} className="module-card">
    <span className="module-icon">{icon}</span>
    <h3>{title}</h3>
    <p>{description}</p>
  </a>
);

const App: React.FC = () => {
  return (
    <Layout>
      <ErrorBoundary>
        <Suspense fallback={<LoadingSpinner message="Loading module..." />}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            
            {/* Each module is loaded independently with its own error boundary */}
            <Route
              path="/reg-reporting/*"
              element={
                <ModuleLoader moduleName="Regulatory Reporting">
                  <RegReporting />
                </ModuleLoader>
              }
            />
            
            <Route
              path="/financial-reporting/*"
              element={
                <ModuleLoader moduleName="Financial Reporting">
                  <FinancialReporting />
                </ModuleLoader>
              }
            />
            
            <Route
              path="/expense-reporting/*"
              element={
                <ModuleLoader moduleName="Expense Reporting">
                  <ExpenseReporting />
                </ModuleLoader>
              }
            />
            
            <Route
              path="/tax-reporting/*"
              element={
                <ModuleLoader moduleName="Tax Reporting">
                  <TaxReporting />
                </ModuleLoader>
              }
            />
            
            <Route
              path="/control-tower/*"
              element={
                <ModuleLoader moduleName="Control Tower">
                  <ControlTower />
                </ModuleLoader>
              }
            />
            
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </Layout>
  );
};

export default App;
