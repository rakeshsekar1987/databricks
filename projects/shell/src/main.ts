import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';

/**
 * Shell Application Entry Point
 * 
 * Bootstraps the main Angular application with standalone components.
 * Module Federation is initialized before the app starts.
 */
bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error('Application bootstrap failed:', err));
