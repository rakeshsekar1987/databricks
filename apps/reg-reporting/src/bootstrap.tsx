import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/module.css';

// Standalone mode - for development or standalone deployment
const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}
