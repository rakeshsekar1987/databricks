/**
 * Authentication Models
 * 
 * Type definitions for OAuth 2.0 authentication
 */

export interface User {
  id: string;
  email: string;
  name: string;
  firstName: string;
  lastName: string;
  roles: string[];
  permissions: string[];
  avatar?: string;
  department?: string;
  title?: string;
}

export interface AuthToken {
  accessToken: string;
  refreshToken?: string;
  idToken?: string;
  tokenType: string;
  expiresIn: number;
  expiresAt: Date;
  scope: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  token: AuthToken | null;
  error: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface OAuthCallbackParams {
  code: string;
  state: string;
  error?: string;
  errorDescription?: string;
}

export interface PKCEChallenge {
  codeVerifier: string;
  codeChallenge: string;
  state: string;
}
