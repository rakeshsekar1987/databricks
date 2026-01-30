import React from 'react';
import TaxReportingGrid from './components/TaxReportingGrid';
import ModuleInfo from './components/ModuleInfo';

/**
 * Tax Reporting Module
 * Uses AG Grid v29.x (different version than other modules)
 * This demonstrates module isolation with different dependency versions
 */
const App: React.FC = () => {
  return (
    <div className="tax-reporting-module">
      <ModuleInfo
        moduleName="Tax Reporting"
        agGridVersion="29.3.0"
        description="Tax calculations, filings, and compliance management"
      />
      
      <div className="module-sections">
        <section className="section">
          <h3>Tax Reports</h3>
          <TaxReportingGrid />
        </section>
      </div>
    </div>
  );
};

export default App;
