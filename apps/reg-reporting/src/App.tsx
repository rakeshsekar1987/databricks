import React from 'react';
import RegReportingGrid from './components/RegReportingGrid';
import ModuleInfo from './components/ModuleInfo';

/**
 * Regulatory Reporting Module
 * This module can run standalone or be loaded as a federated module
 * Uses AG Grid v31.x
 */
const App: React.FC = () => {
  return (
    <div className="reg-reporting-module">
      <ModuleInfo
        moduleName="Regulatory Reporting"
        agGridVersion="31.0.0"
        description="Manage regulatory compliance reports and submissions"
      />
      
      <div className="module-sections">
        <section className="section">
          <h3>Regulatory Reports</h3>
          <RegReportingGrid />
        </section>
      </div>
    </div>
  );
};

export default App;
