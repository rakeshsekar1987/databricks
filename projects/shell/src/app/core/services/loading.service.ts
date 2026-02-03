import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

/**
 * Loading Service
 * 
 * Manages global loading state for the application.
 * Used to show loading indicators during module loading.
 */
@Injectable({
  providedIn: 'root'
})
export class LoadingService {
  private readonly loadingSubject = new BehaviorSubject<boolean>(false);
  private loadingCount = 0;
  
  /**
   * Observable of the current loading state
   */
  readonly isLoading$: Observable<boolean> = this.loadingSubject.asObservable();
  
  /**
   * Starts a loading operation.
   * Supports nested loading calls.
   */
  startLoading(): void {
    this.loadingCount++;
    if (this.loadingCount === 1) {
      this.loadingSubject.next(true);
    }
  }
  
  /**
   * Stops a loading operation.
   * Only hides loading when all operations complete.
   */
  stopLoading(): void {
    this.loadingCount = Math.max(0, this.loadingCount - 1);
    if (this.loadingCount === 0) {
      this.loadingSubject.next(false);
    }
  }
  
  /**
   * Resets loading state immediately.
   * Use for error recovery.
   */
  reset(): void {
    this.loadingCount = 0;
    this.loadingSubject.next(false);
  }
}
