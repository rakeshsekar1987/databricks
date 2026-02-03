import { Injectable, inject, signal } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';

export interface BreadcrumbItem {
  label: string;
  path: string;
}

export interface ModuleNavigation {
  currentModule: string | null;
  previousModule: string | null;
  history: string[];
}

/**
 * Navigation Service
 * 
 * Manages navigation between modules and provides:
 * - Breadcrumb tracking
 * - Navigation history
 * - Module-to-module navigation
 */
@Injectable({
  providedIn: 'root'
})
export class NavigationService {
  private readonly router = inject(Router);
  
  // Navigation state
  private readonly navigationState = signal<ModuleNavigation>({
    currentModule: null,
    previousModule: null,
    history: []
  });
  
  // Module display names
  private readonly moduleNames: Record<string, string> = {
    '': 'Home',
    'reg-reporting': 'Regulatory Reporting',
    'financial-reporting': 'Financial Reporting',
    'expense-reporting': 'Expense Reporting',
    'tax-reporting': 'Tax Reporting',
    'control-tower': 'Control Tower'
  };
  
  // Module routes
  readonly modules = [
    { path: '/reg-reporting', name: 'Regulatory Reporting', icon: '📋', agGrid: 'v31' },
    { path: '/financial-reporting', name: 'Financial Reporting', icon: '💰', agGrid: 'v30' },
    { path: '/expense-reporting', name: 'Expense Reporting', icon: '💳', agGrid: 'v31' },
    { path: '/tax-reporting', name: 'Tax Reporting', icon: '🧾', agGrid: 'v29' },
    { path: '/control-tower', name: 'Control Tower', icon: '🎯', agGrid: 'v31' }
  ];
  
  constructor() {
    this.trackNavigation();
  }
  
  /**
   * Track navigation events
   */
  private trackNavigation(): void {
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd)
    ).subscribe(event => {
      const modulePath = this.extractModulePath(event.urlAfterRedirects);
      
      this.navigationState.update(state => ({
        previousModule: state.currentModule,
        currentModule: modulePath,
        history: [...state.history.slice(-9), modulePath].filter(Boolean)
      }));
    });
  }
  
  /**
   * Extract module path from URL
   */
  private extractModulePath(url: string): string {
    const parts = url.split('/').filter(Boolean);
    return parts[0] || '';
  }
  
  /**
   * Navigate to a module
   */
  navigateTo(modulePath: string): void {
    this.router.navigate([modulePath]);
  }
  
  /**
   * Navigate to previous module
   */
  navigateBack(): void {
    const state = this.navigationState();
    if (state.previousModule) {
      this.router.navigate([`/${state.previousModule}`]);
    } else {
      this.router.navigate(['/']);
    }
  }
  
  /**
   * Get current module name
   */
  getCurrentModuleName(): string {
    const state = this.navigationState();
    return this.moduleNames[state.currentModule || ''] || 'Unknown';
  }
  
  /**
   * Get breadcrumbs for current route
   */
  getBreadcrumbs(): BreadcrumbItem[] {
    const state = this.navigationState();
    const breadcrumbs: BreadcrumbItem[] = [
      { label: 'Home', path: '/' }
    ];
    
    if (state.currentModule && state.currentModule !== '') {
      breadcrumbs.push({
        label: this.moduleNames[state.currentModule] || state.currentModule,
        path: `/${state.currentModule}`
      });
    }
    
    return breadcrumbs;
  }
  
  /**
   * Get navigation history
   */
  getHistory(): string[] {
    return this.navigationState().history;
  }
  
  /**
   * Check if can go back
   */
  canGoBack(): boolean {
    return this.navigationState().previousModule !== null;
  }
  
  /**
   * Get quick navigation links for cross-module navigation
   */
  getQuickLinks(currentModule: string): Array<{ path: string; name: string; icon: string }> {
    return this.modules.filter(m => m.path !== `/${currentModule}`);
  }
}
