import React from 'react';
import Navigation from './Navigation';

interface LayoutProps {
  children: React.ReactNode;
}

/**
 * Main Layout Component
 * Provides consistent structure across all pages
 */
const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="layout">
      <Navigation />
      <main className="main-content" role="main">
        {children}
      </main>
      <footer className="footer" role="contentinfo">
        <div className="footer-content">
          <p>UI Platform - Module Federation Architecture</p>
          <p className="footer-version">
            Environment: {process.env.NODE_ENV || 'development'}
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
