import { HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { tap, catchError, throwError } from 'rxjs';

/**
 * Logging Interceptor
 * 
 * Logs HTTP requests and responses for debugging.
 * In production, sends metrics to monitoring service.
 */
export const loggingInterceptor: HttpInterceptorFn = (req, next) => {
  const startTime = Date.now();
  const requestId = generateRequestId();
  
  // Log request
  console.debug(`[HTTP] ${req.method} ${req.url}`, {
    requestId,
    headers: req.headers.keys(),
    timestamp: new Date().toISOString()
  });
  
  return next(req).pipe(
    tap(event => {
      if (event instanceof HttpResponse) {
        const duration = Date.now() - startTime;
        console.debug(`[HTTP] ${req.method} ${req.url} completed`, {
          requestId,
          status: event.status,
          duration: `${duration}ms`
        });
      }
    }),
    catchError(error => {
      const duration = Date.now() - startTime;
      console.error(`[HTTP] ${req.method} ${req.url} failed`, {
        requestId,
        status: error.status,
        message: error.message,
        duration: `${duration}ms`
      });
      return throwError(() => error);
    })
  );
};

/**
 * Generates a unique request ID for tracing
 */
function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}
