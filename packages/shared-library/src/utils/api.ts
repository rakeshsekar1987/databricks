import type { ApiResponse } from '../types';

interface ApiClientConfig {
  baseUrl: string;
  headers?: Record<string, string>;
  timeout?: number;
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>;
}

/**
 * Creates a configured API client for making HTTP requests
 */
export function createApiClient(config: ApiClientConfig) {
  const { baseUrl, headers: defaultHeaders = {}, timeout = 30000 } = config;

  async function request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const { params, headers: requestHeaders, ...fetchOptions } = options;

    // Build URL with query parameters
    let url = `${baseUrl}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        searchParams.append(key, String(value));
      });
      url += `?${searchParams.toString()}`;
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...defaultHeaders,
          ...requestHeaders,
        },
      });

      clearTimeout(timeoutId);

      const data = await response.json();

      if (!response.ok) {
        return {
          data: data as T,
          success: false,
          message: data.message || `Request failed with status ${response.status}`,
          timestamp: new Date().toISOString(),
        };
      }

      return {
        data: data as T,
        success: true,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      clearTimeout(timeoutId);
      const message = error instanceof Error ? error.message : 'Unknown error occurred';
      return {
        data: null as unknown as T,
        success: false,
        message,
        timestamp: new Date().toISOString(),
      };
    }
  }

  return {
    get: <T>(endpoint: string, options?: RequestOptions) =>
      request<T>(endpoint, { ...options, method: 'GET' }),
    post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
      request<T>(endpoint, { ...options, method: 'POST', body: JSON.stringify(body) }),
    put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
      request<T>(endpoint, { ...options, method: 'PUT', body: JSON.stringify(body) }),
    patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
      request<T>(endpoint, { ...options, method: 'PATCH', body: JSON.stringify(body) }),
    delete: <T>(endpoint: string, options?: RequestOptions) =>
      request<T>(endpoint, { ...options, method: 'DELETE' }),
  };
}
