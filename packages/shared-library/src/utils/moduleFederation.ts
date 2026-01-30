import type { ModuleConfig } from '../types';

// Type for webpack container
interface Container {
  init: (shareScope: Record<string, unknown>) => Promise<void>;
  get: (module: string) => Promise<() => unknown>;
}

declare global {
  interface Window {
    [key: string]: Container | undefined;
  }
}

// Cache for loaded containers
const containerCache = new Map<string, Container>();

/**
 * Dynamically loads a remote module using Module Federation
 */
export async function loadRemoteModule<T = unknown>(
  config: ModuleConfig
): Promise<T> {
  const { remoteEntry, scope, module } = config;

  // Check if container is already loaded
  let container = containerCache.get(scope);

  if (!container) {
    // Load the remote entry script
    await loadRemoteScript(remoteEntry);

    // Get the container from window
    container = window[scope] as Container;
    if (!container) {
      throw new Error(`Container ${scope} not found after loading ${remoteEntry}`);
    }

    // Initialize the container with shared scope
    // @ts-expect-error - __webpack_share_scopes__ is a webpack runtime variable
    await container.init(__webpack_share_scopes__.default);
    containerCache.set(scope, container);
  }

  // Get the module factory
  const factory = await container.get(module);
  if (!factory) {
    throw new Error(`Module ${module} not found in container ${scope}`);
  }

  // Execute factory to get the module
  const Module = factory() as T;
  return Module;
}

/**
 * Preloads a remote module entry script without initializing
 */
export async function preloadRemoteModule(remoteEntry: string): Promise<void> {
  const link = document.createElement('link');
  link.rel = 'preload';
  link.as = 'script';
  link.href = remoteEntry;
  document.head.appendChild(link);
}

/**
 * Loads a remote script and returns a promise when loaded
 */
function loadRemoteScript(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    // Check if script already exists
    const existingScript = document.querySelector(`script[src="${url}"]`);
    if (existingScript) {
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
}
