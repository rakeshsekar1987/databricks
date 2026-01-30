import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  change: string;
  changeType: 'positive' | 'negative' | 'neutral';
  icon: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, change, changeType, icon }) => (
  <div className="metric-card">
    <div className="metric-icon">{icon}</div>
    <div className="metric-content">
      <h4>{title}</h4>
      <div className="metric-value">{value}</div>
      <div className={`metric-change ${changeType}`}>{change}</div>
    </div>
  </div>
);

interface ModuleStatusProps {
  name: string;
  status: 'healthy' | 'warning' | 'error';
  version: string;
  agGridVersion: string;
  lastDeployed: string;
}

const ModuleStatus: React.FC<ModuleStatusProps> = ({ name, status, version, agGridVersion, lastDeployed }) => (
  <div className="module-status-card">
    <div className={`status-indicator ${status}`}></div>
    <div className="module-status-content">
      <h4>{name}</h4>
      <div className="module-meta">
        <span>v{version}</span>
        <span>AG Grid v{agGridVersion}</span>
      </div>
      <div className="last-deployed">Deployed: {lastDeployed}</div>
    </div>
  </div>
);

const Dashboard: React.FC = () => {
  const metrics = [
    { title: 'Total Reports', value: '1,234', change: '+12%', changeType: 'positive' as const, icon: '📊' },
    { title: 'Active Users', value: '856', change: '+5%', changeType: 'positive' as const, icon: '👥' },
    { title: 'Processing Time', value: '1.2s', change: '-15%', changeType: 'positive' as const, icon: '⚡' },
    { title: 'Error Rate', value: '0.02%', change: '+0.01%', changeType: 'negative' as const, icon: '⚠️' },
  ];

  const modules = [
    { name: 'Regulatory Reporting', status: 'healthy' as const, version: '2.1.0', agGridVersion: '31.0.0', lastDeployed: '2024-01-15 10:30' },
    { name: 'Financial Reporting', status: 'healthy' as const, version: '1.5.2', agGridVersion: '30.2.0', lastDeployed: '2024-01-14 15:45' },
    { name: 'Expense Reporting', status: 'warning' as const, version: '1.2.0', agGridVersion: '31.0.0', lastDeployed: '2024-01-13 09:20' },
    { name: 'Tax Reporting', status: 'healthy' as const, version: '3.0.1', agGridVersion: '29.3.0', lastDeployed: '2024-01-12 14:00' },
    { name: 'Control Tower', status: 'healthy' as const, version: '1.0.0', agGridVersion: '31.0.0', lastDeployed: '2024-01-16 08:15' },
  ];

  return (
    <div className="dashboard">
      <section className="metrics-section">
        <h3>Platform Metrics</h3>
        <div className="metrics-grid">
          {metrics.map((metric, index) => (
            <MetricCard key={index} {...metric} />
          ))}
        </div>
      </section>

      <section className="modules-section">
        <h3>Module Status & AG Grid Versions</h3>
        <p className="section-description">Each module runs independently with its own AG Grid version</p>
        <div className="modules-grid">
          {modules.map((module, index) => (
            <ModuleStatus key={index} {...module} />
          ))}
        </div>
      </section>

      <section className="info-section">
        <h3>Module Federation Benefits</h3>
        <div className="benefits-grid">
          <div className="benefit-card">
            <span className="benefit-icon">🚀</span>
            <h4>Independent Deployments</h4>
            <p>Deploy modules without affecting others</p>
          </div>
          <div className="benefit-card">
            <span className="benefit-icon">📦</span>
            <h4>Version Isolation</h4>
            <p>Different AG Grid versions per module</p>
          </div>
          <div className="benefit-card">
            <span className="benefit-icon">👥</span>
            <h4>Parallel Development</h4>
            <p>Teams work independently</p>
          </div>
          <div className="benefit-card">
            <span className="benefit-icon">⚡</span>
            <h4>Faster Builds</h4>
            <p>Only rebuild changed modules</p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
