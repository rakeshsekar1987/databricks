/// <reference types="react" />
/// <reference types="react-dom" />

// Environment variables
declare namespace NodeJS {
  interface ProcessEnv {
    NODE_ENV: 'development' | 'production' | 'test';
    MODULE_REGISTRY_URL?: string;
    ENABLE_DYNAMIC_REMOTES?: string;
    ENABLE_MODULE_PRELOADING?: string;
    API_BASE_URL?: string;
    REG_REPORTING_URL?: string;
    FINANCIAL_REPORTING_URL?: string;
    EXPENSE_REPORTING_URL?: string;
    TAX_REPORTING_URL?: string;
    CONTROL_TOWER_URL?: string;
  }
}

// Hot Module Replacement
interface NodeModule {
  hot?: {
    accept(path?: string, callback?: () => void): void;
  };
}

// Module Federation Remote Types
declare module 'regReporting/App' {
  const Component: React.ComponentType;
  export default Component;
}

declare module 'financialReporting/App' {
  const Component: React.ComponentType;
  export default Component;
}

declare module 'expenseReporting/App' {
  const Component: React.ComponentType;
  export default Component;
}

declare module 'taxReporting/App' {
  const Component: React.ComponentType;
  export default Component;
}

declare module 'controlTower/App' {
  const Component: React.ComponentType;
  export default Component;
}

// CSS Modules
declare module '*.module.css' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

// Assets
declare module '*.svg' {
  const content: string;
  export default content;
}

declare module '*.png' {
  const content: string;
  export default content;
}

declare module '*.jpg' {
  const content: string;
  export default content;
}

// Web Vitals
declare module 'web-vitals' {
  export function getCLS(callback: (metric: { name: string; value: number }) => void): void;
  export function getFID(callback: (metric: { name: string; value: number }) => void): void;
  export function getFCP(callback: (metric: { name: string; value: number }) => void): void;
  export function getLCP(callback: (metric: { name: string; value: number }) => void): void;
  export function getTTFB(callback: (metric: { name: string; value: number }) => void): void;
}
