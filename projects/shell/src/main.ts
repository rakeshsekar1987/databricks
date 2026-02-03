/**
 * Shell Application Entry Point
 * 
 * Uses dynamic import to ensure Module Federation shared modules
 * are properly initialized before the application bootstraps.
 */
import('./bootstrap')
  .catch(err => console.error('Error loading bootstrap:', err));
