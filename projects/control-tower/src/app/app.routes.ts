import { Routes } from '@angular/router';

export const CONTROL_TOWER_ROUTES: Routes = [
  { path: '', loadComponent: () => import('./remote-entry/entry.component').then(m => m.EntryComponent) }
];

export const routes: Routes = [...CONTROL_TOWER_ROUTES, { path: '**', redirectTo: '' }];
