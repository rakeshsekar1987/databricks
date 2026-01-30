import React from 'react';
import { Link } from 'react-router-dom';
import { RemoteConfig } from '@/lib/remoteConfig';

interface HomePageProps {
  remotes: Record<string, RemoteConfig>;
}

/**
 * Home Page Component
 * Displays module cards and platform information
 */
const HomePage: React.FC<HomePageProps> = ({ remotes }) => {
  return (
    <div className="home-page">
      <section className="hero-section">
        <h1>UI Platform</h1>
        <p className="hero-subtitle">
          Module Federation powered micro-frontend architecture
        </p>
        <div className="hero-stats">
          <div className="stat-item">
            <span className="stat-value">{Object.keys(remotes).length}</span>
            <span className="stat-label">Modules</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">3</span>
            <span className="stat-label">AG Grid Versions</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">∞</span>
            <span className="stat-label">Independent Deploys</span>
          </div>
        </div>
      </section>

      <section className="modules-section">
        <h2>Available Modules</h2>
        <div className="module-cards">
          {Object.values(remotes).map((remote) => (
            <ModuleCard key={remote.name} remote={remote} />
          ))}
        </div>
      </section>

      <section className="features-section">
        <h2>Architecture Benefits</h2>
        <div className="features-grid">
          <FeatureCard
            icon="🚀"
            title="Independent Deployments"
            description="Deploy modules without affecting others. No coordinated releases needed."
          />
          <FeatureCard
            icon="📦"
            title="Version Isolation"
            description="Run different AG Grid versions (v29, v30, v31) in the same application."
          />
          <FeatureCard
            icon="👥"
            title="Team Autonomy"
            description="Teams own their modules end-to-end with full deployment independence."
          />
          <FeatureCard
            icon="⚡"
            title="Fast Builds"
            description="Only rebuild changed modules. 80% faster builds on average."
          />
        </div>
      </section>
    </div>
  );
};

interface ModuleCardProps {
  remote: RemoteConfig;
}

const ModuleCard: React.FC<ModuleCardProps> = ({ remote }) => (
  <Link to={remote.path} className="module-card">
    <span className="module-card-icon">{remote.icon}</span>
    <h3 className="module-card-title">{remote.displayName}</h3>
    {remote.agGridVersion && (
      <span className="module-card-version">AG Grid v{remote.agGridVersion}</span>
    )}
    <span className="module-card-arrow">→</span>
  </Link>
);

interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
}

const FeatureCard: React.FC<FeatureCardProps> = ({ icon, title, description }) => (
  <div className="feature-card">
    <span className="feature-icon">{icon}</span>
    <h4 className="feature-title">{title}</h4>
    <p className="feature-description">{description}</p>
  </div>
);

export default HomePage;
