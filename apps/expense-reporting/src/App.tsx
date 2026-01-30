import React from 'react';
import ExpenseGrid from './components/ExpenseGrid';
import ModuleInfo from './components/ModuleInfo';

const App: React.FC = () => (
  <div className="expense-reporting-module">
    <ModuleInfo moduleName="Expense Reporting" agGridVersion="31.0.0" description="Track and manage expenses across the organization" />
    <div className="module-sections">
      <section className="section">
        <h3>Expense Reports</h3>
        <ExpenseGrid />
      </section>
    </div>
  </div>
);

export default App;
