import { Routes } from '@angular/router';
import { loadRemoteModule } from '@angular-architects/module-federation';

/**
 * Application Routes Configuration
 * 
 * Defines routes for the shell application including:
 * - Home page
 * - Lazy-loaded remote modules via Module Federation
 * - Fallback routes
 */
export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/home/home.component').then(m => m.HomeComponent),
    data: { title: 'Home' }
  },
  
  // Regulatory Reporting Module - AG Grid v31
  {
    path: 'reg-reporting',
    loadChildren: () => loadRemoteModule({
      type: 'module',
      remoteEntry: 'http://localhost:4201/remoteEntry.js',
      exposedModule: './routes'
    }).then(m => m.REG_REPORTING_ROUTES).catch(err => {
      console.error('Failed to load Reg Reporting module:', err);
      return import('./features/error/error.routes').then(m => m.ERROR_ROUTES);
    }),
    data: { title: 'Regulatory Reporting', agGridVersion: 'v31' }
  },
  
  // Financial Reporting Module - AG Grid v30
  {
    path: 'financial-reporting',
    loadChildren: () => loadRemoteModule({
      type: 'module',
      remoteEntry: 'http://localhost:4202/remoteEntry.js',
      exposedModule: './routes'
    }).then(m => m.FINANCIAL_REPORTING_ROUTES).catch(err => {
      console.error('Failed to load Financial Reporting module:', err);
      return import('./features/error/error.routes').then(m => m.ERROR_ROUTES);
    }),
    data: { title: 'Financial Reporting', agGridVersion: 'v30' }
  },
  
  // Expense Reporting Module - AG Grid v31
  {
    path: 'expense-reporting',
    loadChildren: () => loadRemoteModule({
      type: 'module',
      remoteEntry: 'http://localhost:4203/remoteEntry.js',
      exposedModule: './routes'
    }).then(m => m.EXPENSE_REPORTING_ROUTES).catch(err => {
      console.error('Failed to load Expense Reporting module:', err);
      return import('./features/error/error.routes').then(m => m.ERROR_ROUTES);
    }),
    data: { title: 'Expense Reporting', agGridVersion: 'v31' }
  },
  
  // Tax Reporting Module - AG Grid v29
  {
    path: 'tax-reporting',
    loadChildren: () => loadRemoteModule({
      type: 'module',
      remoteEntry: 'http://localhost:4204/remoteEntry.js',
      exposedModule: './routes'
    }).then(m => m.TAX_REPORTING_ROUTES).catch(err => {
      console.error('Failed to load Tax Reporting module:', err);
      return import('./features/error/error.routes').then(m => m.ERROR_ROUTES);
    }),
    data: { title: 'Tax Reporting', agGridVersion: 'v29' }
  },
  
  // Control Tower Module - AG Grid v31
  {
    path: 'control-tower',
    loadChildren: () => loadRemoteModule({
      type: 'module',
      remoteEntry: 'http://localhost:4205/remoteEntry.js',
      exposedModule: './routes'
    }).then(m => m.CONTROL_TOWER_ROUTES).catch(err => {
      console.error('Failed to load Control Tower module:', err);
      return import('./features/error/error.routes').then(m => m.ERROR_ROUTES);
    }),
    data: { title: 'Control Tower', agGridVersion: 'v31' }
  },
  
  // Fallback route
  {
    path: '**',
    redirectTo: '',
    pathMatch: 'full'
  }
];
