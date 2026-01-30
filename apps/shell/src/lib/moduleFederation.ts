/**
 * Module Federation Dynamic Remote Loading
 * Production-ready implementation with error handling, retries, and fallbacks
 */

import React from 'react';

// Types
export interface RemoteModuleConfig {
  scope: string;
  module: string;
  url: string;
}

export interface ModuleManifest {
  [key: string]: {
    url: string;
    scope: string;
    module: string;
    version: string;
    agGridVersion?: string;
  };
}

interface Container {
  init(shareScope: Record<string, unknown>): Promise<void>;
  get(module: string): Promise<() => { default: React.ComponentType }>;
}

declare global {
  interface Window {
    __remotes__: Record<string, Container>;
    __webpack_init_sharing__: (scope: string) => Promise<void>;
    __webpack_share_scopes__: { default: Record<string, unknown> };
  }
}

// Cache for loaded containers
const containerCache = new Map<string, Container>();
const moduleCache = new Map<string, React.ComponentType>();
const loadingPromises = new Map<string, Promise<Container>>();

/**
 * Load a remote script with retry logic
 */
async function loadScript(url: string, retries = 3, delay = 1000): Promise<void> {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      await new Promise<void>((resolve, reject) => {
        // Check if already loaded
        const existing = document.querySelector(`script[src="${url}"]`);
        if (existing) {
          resolve();
          return;
        }

        const script = document.createElement('script');
        script.src = url;
        script.type = 'text/javascript';
        script.async = true;

        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`Failed to load script: ${url}`));

        document.head.appendChild(script);
      });
      return;
    } catch (error) {
      if (attempt === retries) {
        throw error;
      }
      // Wait before retry with exponential backoff
      await new Promise((resolve) => setTimeout(resolve, delay * attempt));
    }
  }
}

/**
 * Initialize the share scope for Module Federation
 */
async function initShareScope(): Promise<void> {
  if (!window.__webpack_share_scopes__?.default) {
    await window.__webpack_init_sharing__?.('default');
  }
}

/**
 * Load a remote container
 */
async function loadRemoteContainer(
  scope: string,
  url: string
): Promise<Container> {
  // Check cache first
  if (containerCache.has(scope)) {
    return containerCache.get(scope)!;
  }

  // Check if already loading
  if (loadingPromises.has(scope)) {
    return loadingPromises.get(scope)!;
  }

  const loadPromise = (async () => {
    // Load the remote entry script
    await loadScript(url);

    // Get the container from window
    const container = (window as Record<string, unknown>)[scope] as Container;
    if (!container) {
      throw new Error(`Remote container "${scope}" not found after loading ${url}`);
    }

    // Initialize share scope
    await initShareScope();

    // Initialize the container
    await container.init(window.__webpack_share_scopes__.default);

    // Cache the container
    containerCache.set(scope, container);
    loadingPromises.delete(scope);

    return container;
  })();

  loadingPromises.set(scope, loadPromise);
  return loadPromise;
}

/**
 * Load a remote module component
 */
export async function loadRemoteModule<T = React.ComponentType>(
  config: RemoteModuleConfig
): Promise<T> {
  const { scope, module, url } = config;
  const cacheKey = `${scope}:${module}`;

  // Check module cache
  if (moduleCache.has(cacheKey)) {
    return moduleCache.get(cacheKey) as T;
  }

  try {
    // Load container
    const container = await loadRemoteContainer(scope, url);

    // Get module factory
    const factory = await container.get(module);
    if (!factory) {
      throw new Error(`Module "${module}" not found in container "${scope}"`);
    }

    // Execute factory to get the module
    const moduleExports = factory();
    const Component = moduleExports.default || moduleExports;

    // Cache the module
    moduleCache.set(cacheKey, Component as React.ComponentType);

    return Component as T;
  } catch (error) {
    console.error(`Failed to load remote module: ${scope}/${module}`, error);
    throw error;
  }
}

/**
 * Preload a remote module (for performance optimization)
 */
export function preloadRemoteModule(url: string): void {
  const link = document.createElement('link');
  link.rel = 'preload';
  link.as = 'script';
  link.href = url;
  document.head.appendChild(link);
}

/**
 * Create a lazy-loaded remote component with error boundary
 */
export function createRemoteComponent(
  config: RemoteModuleConfig,
  fallback?: React.ComponentType<{ error?: Error }>
): React.LazyExoticComponent<React.ComponentType<unknown>> {
  return React.lazy(async () => {
    try {
      const Component = await loadRemoteModule<React.ComponentType>(config);
      return { default: Component };
    } catch (error) {
      if (fallback) {
        return { default: fallback };
      }
      throw error;
    }
  });
}

/**
 * Clear the module cache (useful for hot reloading in development)
 */
export function clearModuleCache(): void {
  moduleCache.clear();
  containerCache.clear();
  loadingPromises.clear();
}

/**
 * Get module registry from API
 */
export async function fetchModuleManifest(
  registryUrl: string
): Promise<ModuleManifest> {
  const response = await fetch(`${registryUrl}/api/module-manifest`);
  if (!response.ok) {
    throw new Error(`Failed to fetch module manifest: ${response.statusText}`);
  }
  const data = await response.json();
  return data.modules;
}
