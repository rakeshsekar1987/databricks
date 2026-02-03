import { Routes } from '@angular/router';

/**
 * Error Routes
 * 
 * Fallback routes when a remote module fails to load.
 */
export const ERROR_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./error.component').then(m => m.ErrorComponent)
  },
  {
    path: '**',
    loadComponent: () => import('./error.component').then(m => m.ErrorComponent)
  }
];
