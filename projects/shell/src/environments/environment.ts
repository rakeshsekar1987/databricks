/**
 * Development Environment Configuration
 */
export const environment = {
  production: false,
  
  // Module Registry URL for dynamic remote discovery
  moduleRegistryUrl: 'http://localhost:4000',
  
  // Enable dynamic remote loading (vs static webpack config)
  enableDynamicRemotes: false,
  
  // Remote module URLs
  remotes: {
    regReporting: 'http://localhost:4201/remoteEntry.js',
    financialReporting: 'http://localhost:4202/remoteEntry.js',
    expenseReporting: 'http://localhost:4203/remoteEntry.js',
    taxReporting: 'http://localhost:4204/remoteEntry.js',
    controlTower: 'http://localhost:4205/remoteEntry.js'
  },
  
  // API Configuration
  apiBaseUrl: 'http://localhost:3000/api',
  
  // Feature Flags
  features: {
    modulePreloading: true,
    healthChecks: true,
    analytics: false
  },
  
  // Logging
  logLevel: 'debug'
};
