import { Routes } from '@angular/router';

/**
 * Tax Reporting Routes
 * 
 * Exported for Module Federation consumption by the shell.
 */
export const TAX_REPORTING_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./remote-entry/entry.component').then(m => m.EntryComponent)
  },
  {
    path: 'details/:id',
    loadComponent: () => import('./features/tax-details/tax-details.component').then(m => m.TaxDetailsComponent)
  }
];

// Default routes for standalone mode
export const routes: Routes = [
  ...TAX_REPORTING_ROUTES,
  {
    path: '**',
    redirectTo: ''
  }
];
