/**
 * Remote Module Configuration
 * Manages URLs and configuration for remote modules
 */

import { RemoteModuleConfig } from './moduleFederation';

export interface RemoteConfig {
  name: string;
  displayName: string;
  scope: string;
  module: string;
  url: string;
  path: string;
  icon: string;
  agGridVersion?: string;
}

// Default remote configurations
const defaultRemotes: Record<string, RemoteConfig> = {
  regReporting: {
    name: 'regReporting',
    displayName: 'Regulatory Reporting',
    scope: 'regReporting',
    module: './App',
    url: process.env.REG_REPORTING_URL || 'http://localhost:3001/remoteEntry.js',
    path: '/reg-reporting',
    icon: '📋',
    agGridVersion: '31.0.0',
  },
  financialReporting: {
    name: 'financialReporting',
    displayName: 'Financial Reporting',
    scope: 'financialReporting',
    module: './App',
    url: process.env.FINANCIAL_REPORTING_URL || 'http://localhost:3002/remoteEntry.js',
    path: '/financial-reporting',
    icon: '💰',
    agGridVersion: '30.2.0',
  },
  expenseReporting: {
    name: 'expenseReporting',
    displayName: 'Expense Reporting',
    scope: 'expenseReporting',
    module: './App',
    url: process.env.EXPENSE_REPORTING_URL || 'http://localhost:3003/remoteEntry.js',
    path: '/expense-reporting',
    icon: '💳',
    agGridVersion: '31.0.0',
  },
  taxReporting: {
    name: 'taxReporting',
    displayName: 'Tax Reporting',
    scope: 'taxReporting',
    module: './App',
    url: process.env.TAX_REPORTING_URL || 'http://localhost:3004/remoteEntry.js',
    path: '/tax-reporting',
    icon: '📊',
    agGridVersion: '29.3.0',
  },
  controlTower: {
    name: 'controlTower',
    displayName: 'Control Tower',
    scope: 'controlTower',
    module: './App',
    url: process.env.CONTROL_TOWER_URL || 'http://localhost:3005/remoteEntry.js',
    path: '/control-tower',
    icon: '🎛️',
    agGridVersion: '31.0.0',
  },
};

// Runtime configuration (can be updated from module registry)
let runtimeRemotes: Record<string, RemoteConfig> = { ...defaultRemotes };

/**
 * Get all remote configurations
 */
export function getRemoteConfigs(): Record<string, RemoteConfig> {
  return runtimeRemotes;
}

/**
 * Get a specific remote configuration
 */
export function getRemoteConfig(name: string): RemoteConfig | undefined {
  return runtimeRemotes[name];
}

/**
 * Update remote configurations (from module registry)
 */
export function updateRemoteConfigs(
  updates: Partial<Record<string, Partial<RemoteConfig>>>
): void {
  Object.entries(updates).forEach(([key, update]) => {
    if (runtimeRemotes[key] && update) {
      runtimeRemotes[key] = { ...runtimeRemotes[key], ...update };
    }
  });
}

/**
 * Convert RemoteConfig to RemoteModuleConfig for loading
 */
export function toModuleConfig(remote: RemoteConfig): RemoteModuleConfig {
  return {
    scope: remote.scope,
    module: remote.module,
    url: remote.url,
  };
}

/**
 * Get all navigation items
 */
export function getNavigationItems(): Array<{
  path: string;
  label: string;
  icon: string;
}> {
  return [
    { path: '/', label: 'Home', icon: '🏠' },
    ...Object.values(runtimeRemotes).map((remote) => ({
      path: remote.path,
      label: remote.displayName,
      icon: remote.icon,
    })),
  ];
}
