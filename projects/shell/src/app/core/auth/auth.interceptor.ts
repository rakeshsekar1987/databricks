import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from './auth.service';

/**
 * Authentication Interceptor
 * 
 * Adds Bearer token to outgoing requests and handles 401 responses.
 */
export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) => {
  const authService = inject(AuthService);
  
  // Skip authentication for auth endpoints
  if (isAuthEndpoint(req.url)) {
    return next(req);
  }
  
  // Add Authorization header if token exists
  const token = authService.getAccessToken();
  if (token) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }
  
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        // Token expired, try to refresh
        return authService.refreshToken().pipe(
          switchMap(success => {
            if (success) {
              // Retry request with new token
              const newToken = authService.getAccessToken();
              const retryReq = req.clone({
                setHeaders: {
                  Authorization: `Bearer ${newToken}`
                }
              });
              return next(retryReq);
            }
            // Refresh failed, logout
            authService.logout();
            return throwError(() => error);
          })
        );
      }
      return throwError(() => error);
    })
  );
};

/**
 * Check if URL is an authentication endpoint
 */
function isAuthEndpoint(url: string): boolean {
  const authEndpoints = [
    '/oauth2/token',
    '/oauth2/authorize',
    '/oauth2/userinfo',
    '/oauth2/logout'
  ];
  
  return authEndpoints.some(endpoint => url.includes(endpoint));
}
