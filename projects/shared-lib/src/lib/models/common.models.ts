/**
 * Common Models
 * 
 * Shared type definitions used across modules.
 */

/**
 * Generic API response wrapper
 */
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
  timestamp: string;
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

/**
 * Sort configuration
 */
export interface SortConfig {
  field: string;
  direction: 'asc' | 'desc';
}

/**
 * Filter configuration
 */
export interface FilterConfig {
  field: string;
  operator: 'equals' | 'contains' | 'startsWith' | 'endsWith' | 'gt' | 'lt' | 'gte' | 'lte' | 'between';
  value: unknown;
}

/**
 * Module configuration
 */
export interface ModuleConfig {
  name: string;
  displayName: string;
  description: string;
  remoteEntry: string;
  exposedModule: string;
  routePath: string;
  agGridVersion: string;
  status: 'online' | 'offline' | 'degraded';
}

/**
 * User information
 */
export interface User {
  id: string;
  email: string;
  displayName: string;
  firstName: string;
  lastName: string;
  roles: string[];
  permissions: string[];
}

/**
 * Grid column configuration
 */
export interface GridColumnConfig {
  field: string;
  headerName: string;
  width?: number;
  minWidth?: number;
  flex?: number;
  sortable?: boolean;
  filterable?: boolean;
  editable?: boolean;
  pinned?: 'left' | 'right';
}

/**
 * Status types
 */
export type Status = 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'failed';

/**
 * Priority levels
 */
export type Priority = 'low' | 'medium' | 'high' | 'critical';

/**
 * Environment configuration
 */
export interface Environment {
  production: boolean;
  apiBaseUrl: string;
  moduleRegistryUrl: string;
  enableDynamicRemotes: boolean;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
}
