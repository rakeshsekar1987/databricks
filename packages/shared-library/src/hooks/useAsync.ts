import { useState, useCallback } from 'react';

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

interface UseAsyncReturn<T, P extends unknown[]> extends AsyncState<T> {
  execute: (...args: P) => Promise<T | undefined>;
  reset: () => void;
}

export function useAsync<T, P extends unknown[] = []>(
  asyncFunction: (...args: P) => Promise<T>
): UseAsyncReturn<T, P> {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(
    async (...args: P): Promise<T | undefined> => {
      setState({ data: null, loading: true, error: null });
      try {
        const result = await asyncFunction(...args);
        setState({ data: result, loading: false, error: null });
        return result;
      } catch (error) {
        setState({ data: null, loading: false, error: error as Error });
        return undefined;
      }
    },
    [asyncFunction]
  );

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset };
}
