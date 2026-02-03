import { ErrorHandler, Injectable, NgZone } from '@angular/core';

/**
 * Global Error Handler
 * 
 * Catches and handles all unhandled errors in the application.
 * Provides centralized error logging and user notification.
 */
@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  
  constructor(private zone: NgZone) {}
  
  handleError(error: Error): void {
    // Log error details
    console.error('[GlobalErrorHandler] Unhandled error:', error);
    
    // Run inside Angular zone to ensure change detection
    this.zone.run(() => {
      // Check if it's a chunk loading error (Module Federation)
      if (this.isChunkLoadError(error)) {
        console.warn('[GlobalErrorHandler] Remote module failed to load');
        // Could show a toast notification here
      }
      
      // Log to external service in production
      this.logError(error);
    });
  }
  
  /**
   * Checks if the error is related to chunk/module loading
   */
  private isChunkLoadError(error: Error): boolean {
    const message = error.message || '';
    return (
      message.includes('Loading chunk') ||
      message.includes('ChunkLoadError') ||
      message.includes('remoteEntry') ||
      message.includes('Failed to fetch dynamically imported module')
    );
  }
  
  /**
   * Logs error to external monitoring service
   */
  private logError(error: Error): void {
    // In production, send to error tracking service
    const errorDetails = {
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent
    };
    
    // Example: Send to logging endpoint
    // this.http.post('/api/logs/error', errorDetails).subscribe();
    
    console.debug('[GlobalErrorHandler] Error logged:', errorDetails);
  }
}
