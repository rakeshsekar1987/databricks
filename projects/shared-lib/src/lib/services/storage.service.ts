import { Injectable, PLATFORM_ID, Inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

/**
 * Storage Service
 * 
 * Provides a type-safe wrapper around browser storage APIs.
 * Handles SSR gracefully.
 */
@Injectable({
  providedIn: 'root'
})
export class StorageService {
  private readonly isBrowser: boolean;
  
  constructor(@Inject(PLATFORM_ID) platformId: object) {
    this.isBrowser = isPlatformBrowser(platformId);
  }
  
  /**
   * Gets an item from localStorage
   */
  get<T>(key: string): T | null {
    if (!this.isBrowser) return null;
    
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch (error) {
      console.warn(`[StorageService] Error reading key "${key}":`, error);
      return null;
    }
  }
  
  /**
   * Sets an item in localStorage
   */
  set<T>(key: string, value: T): void {
    if (!this.isBrowser) return;
    
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.warn(`[StorageService] Error setting key "${key}":`, error);
    }
  }
  
  /**
   * Removes an item from localStorage
   */
  remove(key: string): void {
    if (!this.isBrowser) return;
    localStorage.removeItem(key);
  }
  
  /**
   * Clears all items from localStorage
   */
  clear(): void {
    if (!this.isBrowser) return;
    localStorage.clear();
  }
  
  /**
   * Gets an item from sessionStorage
   */
  getSession<T>(key: string): T | null {
    if (!this.isBrowser) return null;
    
    try {
      const item = sessionStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch (error) {
      console.warn(`[StorageService] Error reading session key "${key}":`, error);
      return null;
    }
  }
  
  /**
   * Sets an item in sessionStorage
   */
  setSession<T>(key: string, value: T): void {
    if (!this.isBrowser) return;
    
    try {
      sessionStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.warn(`[StorageService] Error setting session key "${key}":`, error);
    }
  }
}
