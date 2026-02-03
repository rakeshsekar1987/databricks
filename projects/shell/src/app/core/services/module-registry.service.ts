import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of, catchError, map, tap } from 'rxjs';

export interface ModuleConfig {
  name: string;
  remoteEntry: string;
  exposedModule: string;
  displayName: string;
  description: string;
  agGridVersion: string;
  status: 'online' | 'offline' | 'unknown';
  lastHealthCheck?: Date;
}

export interface ModuleManifest {
  version: string;
  modules: Record<string, ModuleConfig>;
  lastUpdated: string;
}

/**
 * Module Registry Service
 * 
 * Manages dynamic module discovery and health monitoring.
 * Provides runtime configuration for Module Federation remotes.
 */
@Injectable({
  providedIn: 'root'
})
export class ModuleRegistryService {
  private readonly http = inject(HttpClient);
  
  private readonly modulesSubject = new BehaviorSubject<Record<string, ModuleConfig>>({});
  readonly modules$: Observable<Record<string, ModuleConfig>> = this.modulesSubject.asObservable();
  
  // Default module configuration
  private readonly defaultModules: Record<string, ModuleConfig> = {
    regReporting: {
      name: 'regReporting',
      remoteEntry: 'http://localhost:4201/remoteEntry.js',
      exposedModule: './Module',
      displayName: 'Regulatory Reporting',
      description: 'Regulatory compliance and reporting',
      agGridVersion: 'v31',
      status: 'unknown'
    },
    financialReporting: {
      name: 'financialReporting',
      remoteEntry: 'http://localhost:4202/remoteEntry.js',
      exposedModule: './Module',
      displayName: 'Financial Reporting',
      description: 'Financial statements and analysis',
      agGridVersion: 'v30',
      status: 'unknown'
    },
    expenseReporting: {
      name: 'expenseReporting',
      remoteEntry: 'http://localhost:4203/remoteEntry.js',
      exposedModule: './Module',
      displayName: 'Expense Reporting',
      description: 'Expense tracking and management',
      agGridVersion: 'v31',
      status: 'unknown'
    },
    taxReporting: {
      name: 'taxReporting',
      remoteEntry: 'http://localhost:4204/remoteEntry.js',
      exposedModule: './Module',
      displayName: 'Tax Reporting',
      description: 'Tax calculations and filing',
      agGridVersion: 'v29',
      status: 'unknown'
    },
    controlTower: {
      name: 'controlTower',
      remoteEntry: 'http://localhost:4205/remoteEntry.js',
      exposedModule: './Module',
      displayName: 'Control Tower',
      description: 'Dashboard and monitoring',
      agGridVersion: 'v31',
      status: 'unknown'
    }
  };
  
  constructor() {
    this.modulesSubject.next(this.defaultModules);
  }
  
  /**
   * Loads module manifest from registry service
   */
  loadManifest(registryUrl: string): Observable<ModuleManifest> {
    return this.http.get<ModuleManifest>(`${registryUrl}/api/module-manifest`).pipe(
      tap(manifest => {
        this.modulesSubject.next(manifest.modules);
      }),
      catchError(error => {
        console.warn('[ModuleRegistry] Failed to load manifest, using defaults:', error);
        return of({
          version: '1.0.0',
          modules: this.defaultModules,
          lastUpdated: new Date().toISOString()
        });
      })
    );
  }
  
  /**
   * Checks health of a remote module
   */
  checkModuleHealth(moduleName: string): Observable<boolean> {
    const module = this.modulesSubject.value[moduleName];
    if (!module) {
      return of(false);
    }
    
    // Check if remoteEntry.js is accessible
    return this.http.head(module.remoteEntry, { observe: 'response' }).pipe(
      map(response => response.status === 200),
      tap(isHealthy => {
        this.updateModuleStatus(moduleName, isHealthy ? 'online' : 'offline');
      }),
      catchError(() => {
        this.updateModuleStatus(moduleName, 'offline');
        return of(false);
      })
    );
  }
  
  /**
   * Updates module status
   */
  private updateModuleStatus(moduleName: string, status: 'online' | 'offline'): void {
    const modules = { ...this.modulesSubject.value };
    if (modules[moduleName]) {
      modules[moduleName] = {
        ...modules[moduleName],
        status,
        lastHealthCheck: new Date()
      };
      this.modulesSubject.next(modules);
    }
  }
  
  /**
   * Gets module configuration by name
   */
  getModule(moduleName: string): ModuleConfig | undefined {
    return this.modulesSubject.value[moduleName];
  }
  
  /**
   * Gets all registered modules
   */
  getAllModules(): ModuleConfig[] {
    return Object.values(this.modulesSubject.value);
  }
}
