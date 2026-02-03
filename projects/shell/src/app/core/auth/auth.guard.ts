import { inject } from '@angular/core';
import { Router, CanActivateFn, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * Authentication Guard
 * 
 * Protects routes that require authentication.
 * Redirects to login page if user is not authenticated.
 */
export const authGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  
  if (authService.isAuthenticated()) {
    return true;
  }
  
  // Store the attempted URL for redirecting after login
  sessionStorage.setItem('auth_redirect_url', state.url);
  
  // Redirect to login
  router.navigate(['/login']);
  return false;
};

/**
 * Role-based Guard
 * 
 * Checks if user has required roles.
 * Configure required roles in route data.
 */
export const roleGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  
  const requiredRoles = route.data['roles'] as string[] || [];
  
  if (requiredRoles.length === 0) {
    return true;
  }
  
  const hasRequiredRole = requiredRoles.some(role => authService.hasRole(role));
  
  if (hasRequiredRole) {
    return true;
  }
  
  // Redirect to unauthorized page or home
  router.navigate(['/']);
  return false;
};

/**
 * Guest Guard
 * 
 * Allows only non-authenticated users.
 * Redirects authenticated users to home.
 */
export const guestGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);
  
  if (!authService.isAuthenticated()) {
    return true;
  }
  
  router.navigate(['/']);
  return false;
};
