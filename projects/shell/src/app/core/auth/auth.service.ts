import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, of, throwError, BehaviorSubject } from 'rxjs';
import { map, tap, catchError, delay } from 'rxjs/operators';

import { 
  User, 
  AuthToken, 
  AuthState, 
  LoginCredentials, 
  OAuthCallbackParams,
  PKCEChallenge 
} from './auth.models';
import { OAUTH_CONFIG, USE_MOCK_AUTH, MOCK_USER } from './auth.config';

/**
 * Authentication Service
 * 
 * Handles OAuth 2.0 authentication with domain_name.com
 * Supports:
 * - Authorization Code Flow with PKCE
 * - Token refresh
 * - User session management
 * - Mock authentication for development
 */
@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  
  // Auth state using signals for reactivity
  private readonly authState = signal<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    user: null,
    token: null,
    error: null
  });
  
  // Computed signals for easy access
  readonly isAuthenticated = computed(() => this.authState().isAuthenticated);
  readonly isLoading = computed(() => this.authState().isLoading);
  readonly currentUser = computed(() => this.authState().user);
  readonly authError = computed(() => this.authState().error);
  
  // Storage keys
  private readonly TOKEN_KEY = 'auth_token';
  private readonly USER_KEY = 'auth_user';
  private readonly PKCE_KEY = 'auth_pkce';
  
  constructor() {
    this.initializeAuth();
  }
  
  /**
   * Initialize authentication state from storage
   */
  private initializeAuth(): void {
    const storedToken = this.getStoredToken();
    const storedUser = this.getStoredUser();
    
    if (storedToken && storedUser && !this.isTokenExpired(storedToken)) {
      this.authState.set({
        isAuthenticated: true,
        isLoading: false,
        user: storedUser,
        token: storedToken,
        error: null
      });
    } else {
      this.clearStorage();
      this.authState.update(state => ({ ...state, isLoading: false }));
    }
  }
  
  /**
   * Initiates OAuth 2.0 login flow
   */
  login(): void {
    if (USE_MOCK_AUTH) {
      this.mockLogin();
      return;
    }
    
    // Generate PKCE challenge
    const pkce = this.generatePKCE();
    sessionStorage.setItem(this.PKCE_KEY, JSON.stringify(pkce));
    
    // Build authorization URL
    const params = new URLSearchParams({
      client_id: OAUTH_CONFIG.clientId,
      redirect_uri: OAUTH_CONFIG.redirectUri,
      response_type: OAUTH_CONFIG.responseType,
      scope: OAUTH_CONFIG.scope,
      state: pkce.state,
      code_challenge: pkce.codeChallenge,
      code_challenge_method: 'S256'
    });
    
    // Redirect to OAuth provider
    window.location.href = `${OAUTH_CONFIG.authorizationEndpoint}?${params.toString()}`;
  }
  
  /**
   * Mock login for development
   */
  private mockLogin(): void {
    this.authState.update(state => ({ ...state, isLoading: true }));
    
    // Simulate API delay
    setTimeout(() => {
      const mockToken: AuthToken = {
        accessToken: 'mock_access_token_' + Date.now(),
        refreshToken: 'mock_refresh_token_' + Date.now(),
        idToken: 'mock_id_token_' + Date.now(),
        tokenType: 'Bearer',
        expiresIn: 3600,
        expiresAt: new Date(Date.now() + 3600 * 1000),
        scope: 'openid profile email'
      };
      
      this.storeToken(mockToken);
      this.storeUser(MOCK_USER);
      
      this.authState.set({
        isAuthenticated: true,
        isLoading: false,
        user: MOCK_USER,
        token: mockToken,
        error: null
      });
      
      console.log('[AuthService] Mock login successful');
      this.router.navigate(['/']);
    }, 800);
  }
  
  /**
   * Handle OAuth callback
   */
  handleCallback(params: OAuthCallbackParams): Observable<boolean> {
    if (params.error) {
      this.authState.update(state => ({
        ...state,
        isLoading: false,
        error: params.errorDescription ?? params.error ?? 'Authentication error'
      }));
      return of(false);
    }
    
    const storedPKCE = sessionStorage.getItem(this.PKCE_KEY);
    if (!storedPKCE) {
      this.authState.update(state => ({
        ...state,
        isLoading: false,
        error: 'Authentication state not found'
      }));
      return of(false);
    }
    
    const pkce: PKCEChallenge = JSON.parse(storedPKCE);
    
    // Verify state
    if (params.state !== pkce.state) {
      this.authState.update(state => ({
        ...state,
        isLoading: false,
        error: 'Invalid state parameter'
      }));
      return of(false);
    }
    
    // Exchange code for tokens
    return this.exchangeCodeForTokens(params.code, pkce.codeVerifier);
  }
  
  /**
   * Exchange authorization code for tokens
   */
  private exchangeCodeForTokens(code: string, codeVerifier: string): Observable<boolean> {
    const body = new HttpParams()
      .set('grant_type', 'authorization_code')
      .set('client_id', OAUTH_CONFIG.clientId)
      .set('redirect_uri', OAUTH_CONFIG.redirectUri)
      .set('code', code)
      .set('code_verifier', codeVerifier);
    
    const headers = new HttpHeaders({
      'Content-Type': 'application/x-www-form-urlencoded'
    });
    
    return this.http.post<any>(OAUTH_CONFIG.tokenEndpoint, body.toString(), { headers }).pipe(
      tap(response => {
        const token: AuthToken = {
          accessToken: response.access_token,
          refreshToken: response.refresh_token,
          idToken: response.id_token,
          tokenType: response.token_type,
          expiresIn: response.expires_in,
          expiresAt: new Date(Date.now() + response.expires_in * 1000),
          scope: response.scope
        };
        
        this.storeToken(token);
        sessionStorage.removeItem(this.PKCE_KEY);
      }),
      map(() => this.fetchUserInfo()),
      map(() => true),
      catchError(error => {
        this.authState.update(state => ({
          ...state,
          isLoading: false,
          error: 'Failed to exchange authorization code'
        }));
        return of(false);
      })
    );
  }
  
  /**
   * Fetch user info from OAuth provider
   */
  private fetchUserInfo(): void {
    const token = this.getStoredToken();
    if (!token) return;
    
    this.http.get<any>(OAUTH_CONFIG.userInfoEndpoint, {
      headers: { Authorization: `Bearer ${token.accessToken}` }
    }).subscribe({
      next: (userInfo) => {
        const user: User = {
          id: userInfo.sub,
          email: userInfo.email,
          name: userInfo.name,
          firstName: userInfo.given_name,
          lastName: userInfo.family_name,
          roles: userInfo.roles || ['user'],
          permissions: userInfo.permissions || ['read']
        };
        
        this.storeUser(user);
        this.authState.set({
          isAuthenticated: true,
          isLoading: false,
          user,
          token,
          error: null
        });
      },
      error: () => {
        this.authState.update(state => ({
          ...state,
          isLoading: false,
          error: 'Failed to fetch user information'
        }));
      }
    });
  }
  
  /**
   * Logout user
   */
  logout(): void {
    this.clearStorage();
    
    this.authState.set({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      token: null,
      error: null
    });
    
    if (USE_MOCK_AUTH) {
      this.router.navigate(['/login']);
      return;
    }
    
    // Redirect to OAuth logout
    const params = new URLSearchParams({
      client_id: OAUTH_CONFIG.clientId,
      post_logout_redirect_uri: OAUTH_CONFIG.postLogoutRedirectUri
    });
    
    window.location.href = `${OAUTH_CONFIG.logoutEndpoint}?${params.toString()}`;
  }
  
  /**
   * Refresh access token
   */
  refreshToken(): Observable<boolean> {
    const token = this.getStoredToken();
    if (!token?.refreshToken) {
      return of(false);
    }
    
    const body = new HttpParams()
      .set('grant_type', 'refresh_token')
      .set('client_id', OAUTH_CONFIG.clientId)
      .set('refresh_token', token.refreshToken);
    
    const headers = new HttpHeaders({
      'Content-Type': 'application/x-www-form-urlencoded'
    });
    
    return this.http.post<any>(OAUTH_CONFIG.tokenEndpoint, body.toString(), { headers }).pipe(
      tap(response => {
        const newToken: AuthToken = {
          ...token,
          accessToken: response.access_token,
          refreshToken: response.refresh_token || token.refreshToken,
          expiresIn: response.expires_in,
          expiresAt: new Date(Date.now() + response.expires_in * 1000)
        };
        
        this.storeToken(newToken);
        this.authState.update(state => ({ ...state, token: newToken }));
      }),
      map(() => true),
      catchError(() => {
        this.logout();
        return of(false);
      })
    );
  }
  
  /**
   * Get current access token
   */
  getAccessToken(): string | null {
    const token = this.getStoredToken();
    if (!token || this.isTokenExpired(token)) {
      return null;
    }
    return token.accessToken;
  }
  
  /**
   * Check if user has specific role
   */
  hasRole(role: string): boolean {
    return this.currentUser()?.roles?.includes(role) ?? false;
  }
  
  /**
   * Check if user has specific permission
   */
  hasPermission(permission: string): boolean {
    return this.currentUser()?.permissions?.includes(permission) ?? false;
  }
  
  // Storage helpers
  private storeToken(token: AuthToken): void {
    localStorage.setItem(this.TOKEN_KEY, JSON.stringify(token));
  }
  
  private storeUser(user: User): void {
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  }
  
  private getStoredToken(): AuthToken | null {
    const stored = localStorage.getItem(this.TOKEN_KEY);
    if (!stored) return null;
    
    const token = JSON.parse(stored);
    token.expiresAt = new Date(token.expiresAt);
    return token;
  }
  
  private getStoredUser(): User | null {
    const stored = localStorage.getItem(this.USER_KEY);
    return stored ? JSON.parse(stored) : null;
  }
  
  private clearStorage(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    sessionStorage.removeItem(this.PKCE_KEY);
  }
  
  private isTokenExpired(token: AuthToken): boolean {
    return new Date() >= token.expiresAt;
  }
  
  // PKCE helpers
  private generatePKCE(): PKCEChallenge {
    const codeVerifier = this.generateRandomString(64);
    const codeChallenge = this.base64UrlEncode(codeVerifier);
    const state = this.generateRandomString(32);
    
    return { codeVerifier, codeChallenge, state };
  }
  
  private generateRandomString(length: number): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
    let result = '';
    const randomValues = new Uint8Array(length);
    crypto.getRandomValues(randomValues);
    randomValues.forEach(v => result += chars[v % chars.length]);
    return result;
  }
  
  private base64UrlEncode(str: string): string {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    return btoa(String.fromCharCode(...data))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');
  }
}
