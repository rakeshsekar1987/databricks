import { Routes } from '@angular/router';

export const EXPENSE_REPORTING_ROUTES: Routes = [
  { path: '', loadComponent: () => import('./remote-entry/entry.component').then(m => m.EntryComponent) }
];

export const routes: Routes = [...EXPENSE_REPORTING_ROUTES, { path: '**', redirectTo: '' }];
