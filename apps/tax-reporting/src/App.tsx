import React from 'react';
import TaxReportingGrid from './components/TaxReportingGrid';
import './styles/module.css';

// Get AG Grid version from build-time env
const AG_GRID_VERSION = process.env.AG_GRID_VERSION || '29.3.0';

/**
 * Tax Reporting Module
 * 
 * This module uses AG Grid v29.x for legacy compatibility.
 * It demonstrates how Module Federation allows different versions
 * of the same dependency across modules.
 */
const App: React.FC = () => {
  return (
    <div className="tax-reporting-module">
      <ModuleHeader />
      <div className="module-sections">
        <section className="section">
          <h3>Tax Reports</h3>
          <TaxReportingGrid />
        </section>
      </div>
    </div>
  );
};

const ModuleHeader: React.FC = () => (
  <div className="module-info">
    <div className="module-info-header">
      <h2>Tax Reporting</h2>
      <span className="version-badge">AG Grid v{AG_GRID_VERSION}</span>
    </div>
    <p className="module-description">
      Tax calculations, filings, and compliance management.
      Using AG Grid v29.x for legacy feature compatibility.
    </p>
  </div>
);

export default App;
