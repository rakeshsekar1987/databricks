import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Home', icon: '🏠' },
  { path: '/reg-reporting', label: 'Reg Reporting', icon: '📋' },
  { path: '/financial-reporting', label: 'Financial Reporting', icon: '💰' },
  { path: '/expense-reporting', label: 'Expense Reporting', icon: '💳' },
  { path: '/tax-reporting', label: 'Tax Reporting', icon: '📊' },
  { path: '/control-tower', label: 'Control Tower', icon: '🎛️' },
];

const Navigation: React.FC = () => {
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="navigation">
      <div className="nav-brand">
        <Link to="/" className="brand-link">
          <span className="brand-icon">🚀</span>
          <span className="brand-text">UI Platform</span>
        </Link>
      </div>

      <button
        className="menu-toggle"
        onClick={() => setIsMenuOpen(!isMenuOpen)}
        aria-label="Toggle navigation"
      >
        <span className="menu-icon">{isMenuOpen ? '✕' : '☰'}</span>
      </button>

      <ul className={`nav-links ${isMenuOpen ? 'open' : ''}`}>
        {navItems.map((item) => (
          <li key={item.path}>
            <Link
              to={item.path}
              className={`nav-link ${isActive(item.path) ? 'active' : ''}`}
              onClick={() => setIsMenuOpen(false)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </Link>
          </li>
        ))}
      </ul>

      <div className="nav-actions">
        <button className="theme-toggle" aria-label="Toggle theme">
          🌙
        </button>
        <div className="user-menu">
          <span className="user-avatar">👤</span>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
