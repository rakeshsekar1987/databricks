import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';

/**
 * Tax Reporting Module Entry Point
 * 
 * Can run standalone or be loaded as a federated module.
 */
bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error('Tax Reporting bootstrap failed:', err));
