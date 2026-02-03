import { ApplicationConfig, ErrorHandler, importProvidersFrom } from '@angular/core';
import { provideRouter, withPreloading, PreloadAllModules, withRouterConfig } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';

import { routes } from './app.routes';
import { GlobalErrorHandler } from './core/services/global-error-handler.service';
import { loggingInterceptor } from './core/interceptors/logging.interceptor';

/**
 * Application Configuration
 * 
 * Configures providers for the root application including:
 * - Router with preloading strategy
 * - HTTP client with interceptors
 * - Animations
 * - Global error handling
 */
export const appConfig: ApplicationConfig = {
  providers: [
    // Router configuration with preloading for better performance
    provideRouter(
      routes,
      withPreloading(PreloadAllModules),
      withRouterConfig({
        onSameUrlNavigation: 'reload',
        paramsInheritanceStrategy: 'always'
      })
    ),
    
    // HTTP client with logging interceptor
    provideHttpClient(
      withInterceptors([loggingInterceptor])
    ),
    
    // Enable animations for Motif components
    provideAnimations(),
    
    // Global error handler for unhandled errors
    {
      provide: ErrorHandler,
      useClass: GlobalErrorHandler
    }
  ]
};
