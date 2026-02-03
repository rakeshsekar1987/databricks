import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError, shareReplay } from 'rxjs/operators';

/**
 * Mock Data Service
 * 
 * Provides mock JSON data for all modules.
 * In production, this would be replaced with actual API calls.
 */
@Injectable({
  providedIn: 'root'
})
export class MockDataService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/assets/mock-data';
  
  // Cache for loaded data
  private cache = new Map<string, Observable<any>>();
  
  /**
   * Get tax reports data
   */
  getTaxReports(): Observable<any[]> {
    return this.loadData('tax-reports.json').pipe(
      map(response => response.data)
    );
  }
  
  /**
   * Get financial statements data
   */
  getFinancialStatements(): Observable<any[]> {
    return this.loadData('financial-statements.json').pipe(
      map(response => response.data)
    );
  }
  
  /**
   * Get regulatory reports data
   */
  getRegulatoryReports(): Observable<any[]> {
    return this.loadData('regulatory-reports.json').pipe(
      map(response => response.data)
    );
  }
  
  /**
   * Get expenses data
   */
  getExpenses(): Observable<any[]> {
    return this.loadData('expenses.json').pipe(
      map(response => response.data)
    );
  }
  
  /**
   * Get modules status for control tower
   */
  getModulesStatus(): Observable<any> {
    return this.loadData('modules-status.json');
  }
  
  /**
   * Load data from JSON file with caching
   */
  private loadData(filename: string): Observable<any> {
    const url = `${this.baseUrl}/${filename}`;
    
    if (!this.cache.has(url)) {
      this.cache.set(
        url,
        this.http.get<any>(url).pipe(
          shareReplay(1),
          catchError(error => {
            console.error(`[MockDataService] Failed to load ${filename}:`, error);
            return of({ data: [], meta: {} });
          })
        )
      );
    }
    
    return this.cache.get(url)!;
  }
  
  /**
   * Clear cache (useful for refresh)
   */
  clearCache(): void {
    this.cache.clear();
  }
}
