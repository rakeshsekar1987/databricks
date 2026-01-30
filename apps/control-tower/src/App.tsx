import React from 'react';
import Dashboard from './components/Dashboard';
import ModuleInfo from './components/ModuleInfo';

const App: React.FC = () => (
  <div className="control-tower-module">
    <ModuleInfo moduleName="Control Tower" agGridVersion="31.0.0" description="Real-time dashboard and system monitoring" />
    <Dashboard />
  </div>
);

export default App;
