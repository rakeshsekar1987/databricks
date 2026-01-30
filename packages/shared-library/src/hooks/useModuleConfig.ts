import { useState, useEffect } from 'react';
import type { ModuleManifest, ModuleConfig } from '../types';

interface UseModuleConfigOptions {
  manifestUrl?: string;
  pollInterval?: number;
}

interface UseModuleConfigReturn {
  modules: Record<string, ModuleConfig>;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

const defaultManifestUrl = '/api/module-manifest';

export function useModuleConfig(options: UseModuleConfigOptions = {}): UseModuleConfigReturn {
  const { manifestUrl = defaultManifestUrl, pollInterval } = options;
  
  const [modules, setModules] = useState<Record<string, ModuleConfig>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchManifest = async () => {
    try {
      setLoading(true);
      const response = await fetch(manifestUrl);
      if (!response.ok) {
        throw new Error(`Failed to fetch module manifest: ${response.statusText}`);
      }
      const manifest: ModuleManifest = await response.json();
      setModules(manifest.modules);
      setError(null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchManifest();

    if (pollInterval && pollInterval > 0) {
      const interval = setInterval(fetchManifest, pollInterval);
      return () => clearInterval(interval);
    }
  }, [manifestUrl, pollInterval]);

  return { modules, loading, error, refresh: fetchManifest };
}
