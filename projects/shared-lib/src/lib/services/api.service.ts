import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';

export interface ApiOptions {
  params?: Record<string, string | number | boolean>;
  headers?: Record<string, string>;
  retries?: number;
}

/**
 * API Service
 * 
 * Provides a centralized HTTP client with error handling and retry logic.
 */
@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly http = inject(HttpClient);
  private baseUrl = '';
  
  /**
   * Sets the base URL for API requests
   */
  setBaseUrl(url: string): void {
    this.baseUrl = url;
  }
  
  /**
   * GET request
   */
  get<T>(endpoint: string, options?: ApiOptions): Observable<T> {
    return this.http.get<T>(this.buildUrl(endpoint), this.buildOptions(options)).pipe(
      retry(options?.retries ?? 0),
      catchError(this.handleError)
    );
  }
  
  /**
   * POST request
   */
  post<T>(endpoint: string, body: unknown, options?: ApiOptions): Observable<T> {
    return this.http.post<T>(this.buildUrl(endpoint), body, this.buildOptions(options)).pipe(
      catchError(this.handleError)
    );
  }
  
  /**
   * PUT request
   */
  put<T>(endpoint: string, body: unknown, options?: ApiOptions): Observable<T> {
    return this.http.put<T>(this.buildUrl(endpoint), body, this.buildOptions(options)).pipe(
      catchError(this.handleError)
    );
  }
  
  /**
   * PATCH request
   */
  patch<T>(endpoint: string, body: unknown, options?: ApiOptions): Observable<T> {
    return this.http.patch<T>(this.buildUrl(endpoint), body, this.buildOptions(options)).pipe(
      catchError(this.handleError)
    );
  }
  
  /**
   * DELETE request
   */
  delete<T>(endpoint: string, options?: ApiOptions): Observable<T> {
    return this.http.delete<T>(this.buildUrl(endpoint), this.buildOptions(options)).pipe(
      catchError(this.handleError)
    );
  }
  
  private buildUrl(endpoint: string): string {
    if (endpoint.startsWith('http')) {
      return endpoint;
    }
    return `${this.baseUrl}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  }
  
  private buildOptions(options?: ApiOptions): { params?: HttpParams; headers?: HttpHeaders } {
    const result: { params?: HttpParams; headers?: HttpHeaders } = {};
    
    if (options?.params) {
      let params = new HttpParams();
      Object.entries(options.params).forEach(([key, value]) => {
        params = params.set(key, String(value));
      });
      result.params = params;
    }
    
    if (options?.headers) {
      result.headers = new HttpHeaders(options.headers);
    }
    
    return result;
  }
  
  private handleError(error: HttpErrorResponse): Observable<never> {
    let message = 'An error occurred';
    
    if (error.error instanceof ErrorEvent) {
      // Client-side error
      message = error.error.message;
    } else {
      // Server-side error
      message = error.error?.message || `Server returned ${error.status}`;
    }
    
    console.error('[ApiService] Error:', message);
    return throwError(() => new Error(message));
  }
}
