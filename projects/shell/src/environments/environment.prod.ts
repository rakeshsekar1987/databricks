/**
 * Production Environment Configuration
 */
export const environment = {
  production: true,
  
  // Module Registry URL for dynamic remote discovery
  moduleRegistryUrl: 'https://module-registry.example.com',
  
  // Enable dynamic remote loading in production
  enableDynamicRemotes: true,
  
  // Remote module URLs (production CDN)
  remotes: {
    regReporting: 'https://cdn.example.com/reg-reporting/latest/remoteEntry.js',
    financialReporting: 'https://cdn.example.com/financial-reporting/latest/remoteEntry.js',
    expenseReporting: 'https://cdn.example.com/expense-reporting/latest/remoteEntry.js',
    taxReporting: 'https://cdn.example.com/tax-reporting/latest/remoteEntry.js',
    controlTower: 'https://cdn.example.com/control-tower/latest/remoteEntry.js'
  },
  
  // API Configuration
  apiBaseUrl: 'https://api.example.com',
  
  // Feature Flags
  features: {
    modulePreloading: true,
    healthChecks: true,
    analytics: true
  },
  
  // Logging
  logLevel: 'error'
};
