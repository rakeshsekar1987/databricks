// Common types used across modules

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user' | 'viewer';
  department: string;
}

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface ModuleConfig {
  name: string;
  version: string;
  remoteEntry: string;
  scope: string;
  module: string;
}

export interface ModuleManifest {
  name: string;
  version: string;
  modules: Record<string, ModuleConfig>;
  updatedAt: string;
}

export type Status = 'pending' | 'active' | 'completed' | 'cancelled' | 'error';

export interface AuditLog {
  id: string;
  action: string;
  userId: string;
  timestamp: string;
  details: Record<string, unknown>;
}
