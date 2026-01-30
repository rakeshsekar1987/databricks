import React from 'react';
import FinancialGrid from './components/FinancialGrid';
import ModuleInfo from './components/ModuleInfo';

/**
 * Financial Reporting Module
 * Uses AG Grid v30.x
 */
const App: React.FC = () => {
  return (
    <div className="financial-reporting-module">
      <ModuleInfo
        moduleName="Financial Reporting"
        agGridVersion="30.2.0"
        description="Financial statements, analytics, and reporting"
      />
      <div className="module-sections">
        <section className="section">
          <h3>Financial Reports</h3>
          <FinancialGrid />
        </section>
      </div>
    </div>
  );
};

export default App;
