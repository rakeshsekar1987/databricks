import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './styles/global.css';

/**
 * Bootstrap Application
 * Entry point after Module Federation initialization
 */

// Get root element
const container = document.getElementById('root');

if (!container) {
  throw new Error('Root container element not found');
}

// Create React root
const root = createRoot(container);

// Render application
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

// Enable hot module replacement in development
if (process.env.NODE_ENV === 'development' && module.hot) {
  module.hot.accept('./App', () => {
    const NextApp = require('./App').default;
    root.render(
      <React.StrictMode>
        <BrowserRouter>
          <NextApp />
        </BrowserRouter>
      </React.StrictMode>
    );
  });
}

// Performance monitoring
if (process.env.NODE_ENV === 'production') {
  // Report Web Vitals
  import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
    const reportMetric = (metric: { name: string; value: number }) => {
      // Send to analytics
      console.info('[Performance]', metric.name, metric.value);
    };

    getCLS(reportMetric);
    getFID(reportMetric);
    getFCP(reportMetric);
    getLCP(reportMetric);
    getTTFB(reportMetric);
  }).catch(() => {
    // web-vitals not available
  });
}
