/**
 * OAuth 2.0 Configuration
 * 
 * Configuration for SSO authentication with domain_name.com
 * Supports Authorization Code Flow with PKCE
 */

export interface OAuthConfig {
  issuer: string;
  clientId: string;
  redirectUri: string;
  postLogoutRedirectUri: string;
  scope: string;
  responseType: string;
  authorizationEndpoint: string;
  tokenEndpoint: string;
  userInfoEndpoint: string;
  logoutEndpoint: string;
}

export const OAUTH_CONFIG: OAuthConfig = {
  // OAuth 2.0 Provider (domain_name.com)
  issuer: 'https://auth.domain_name.com',
  
  // Client ID registered with the OAuth provider
  clientId: 'ui-module-federation-client',
  
  // Redirect URIs
  redirectUri: 'http://localhost:4200/auth/callback',
  postLogoutRedirectUri: 'http://localhost:4200',
  
  // OAuth scopes
  scope: 'openid profile email',
  
  // Response type for Authorization Code Flow
  responseType: 'code',
  
  // OAuth endpoints
  authorizationEndpoint: 'https://auth.domain_name.com/oauth2/authorize',
  tokenEndpoint: 'https://auth.domain_name.com/oauth2/token',
  userInfoEndpoint: 'https://auth.domain_name.com/oauth2/userinfo',
  logoutEndpoint: 'https://auth.domain_name.com/oauth2/logout'
};

/**
 * Development/Mock configuration
 * Set USE_MOCK_AUTH to true for local development without OAuth provider
 */
export const USE_MOCK_AUTH = true;

export const MOCK_USER = {
  id: 'user-001',
  email: 'john.doe@domain_name.com',
  name: 'John Doe',
  firstName: 'John',
  lastName: 'Doe',
  roles: ['user', 'admin'],
  permissions: ['read', 'write', 'delete'],
  avatar: 'JD',
  department: 'Technology',
  title: 'Senior Developer'
};
