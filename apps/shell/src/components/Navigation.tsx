import React, { useState, useCallback, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getNavigationItems } from '@/lib/remoteConfig';

/**
 * Navigation Component
 * Responsive navigation with mobile support
 */
const Navigation: React.FC = () => {
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const navItems = getNavigationItems();

  // Check if current path is active
  const isActive = useCallback(
    (path: string) => {
      if (path === '/') {
        return location.pathname === '/';
      }
      return location.pathname.startsWith(path);
    },
    [location.pathname]
  );

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth >= 768) {
        setIsMenuOpen(false);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Close menu on navigation
  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsMenuOpen(false);
    }
  };

  return (
    <nav className="navigation" role="navigation" aria-label="Main navigation">
      <div className="nav-container">
        {/* Brand */}
        <div className="nav-brand">
          <Link to="/" className="brand-link" aria-label="Home">
            <span className="brand-icon">🚀</span>
            <span className="brand-text">UI Platform</span>
          </Link>
        </div>

        {/* Mobile Menu Toggle */}
        {isMobile && (
          <button
            className="menu-toggle"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            onKeyDown={handleKeyDown}
            aria-expanded={isMenuOpen}
            aria-controls="nav-menu"
            aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
          >
            <span className="menu-icon">{isMenuOpen ? '✕' : '☰'}</span>
          </button>
        )}

        {/* Navigation Links */}
        <ul
          id="nav-menu"
          className={`nav-links ${isMenuOpen ? 'open' : ''}`}
          role="menubar"
        >
          {navItems.map((item) => (
            <li key={item.path} role="none">
              <Link
                to={item.path}
                className={`nav-link ${isActive(item.path) ? 'active' : ''}`}
                role="menuitem"
                aria-current={isActive(item.path) ? 'page' : undefined}
              >
                <span className="nav-icon" aria-hidden="true">
                  {item.icon}
                </span>
                <span className="nav-label">{item.label}</span>
              </Link>
            </li>
          ))}
        </ul>

        {/* User Actions */}
        <div className="nav-actions">
          <button
            className="theme-toggle"
            aria-label="Toggle dark mode"
            onClick={() => {
              // Theme toggle implementation
              document.body.classList.toggle('dark-mode');
            }}
          >
            🌙
          </button>
          <div className="user-menu">
            <button className="user-avatar" aria-label="User menu">
              👤
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
