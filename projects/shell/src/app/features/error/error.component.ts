import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

/**
 * Error Component
 * 
 * Displayed when a remote module fails to load.
 * Provides retry functionality and navigation back to home.
 */
@Component({
  selector: 'app-error',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="error-container">
      <div class="error-content">
        <div class="error-icon">⚠️</div>
        <h1>Module Unavailable</h1>
        <p>The requested module could not be loaded. This might be because:</p>
        <ul>
          <li>The module service is temporarily unavailable</li>
          <li>There was a network connectivity issue</li>
          <li>The module is being updated</li>
        </ul>
        
        <div class="error-actions">
          <button class="btn-primary" (click)="retry()">
            🔄 Retry
          </button>
          <a routerLink="/" class="btn-secondary">
            🏠 Go to Home
          </a>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .error-container {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 60vh;
      padding: 24px;
    }
    
    .error-content {
      text-align: center;
      max-width: 500px;
      padding: 48px;
      background: white;
      border-radius: 16px;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
    }
    
    .error-icon {
      font-size: 4rem;
      margin-bottom: 24px;
    }
    
    h1 {
      margin: 0 0 16px 0;
      font-size: 1.75rem;
      color: #1a1a2e;
    }
    
    p {
      color: #666;
      margin-bottom: 16px;
    }
    
    ul {
      text-align: left;
      color: #666;
      margin-bottom: 32px;
    }
    
    li {
      margin-bottom: 8px;
    }
    
    .error-actions {
      display: flex;
      gap: 16px;
      justify-content: center;
    }
    
    .btn-primary,
    .btn-secondary {
      padding: 12px 24px;
      border-radius: 8px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.2s;
    }
    
    .btn-primary {
      background: #1976d2;
      color: white;
      border: none;
    }
    
    .btn-primary:hover {
      background: #1565c0;
    }
    
    .btn-secondary {
      background: #f5f5f5;
      color: #333;
      border: 1px solid #e0e0e0;
    }
    
    .btn-secondary:hover {
      background: #eeeeee;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ErrorComponent {
  retry(): void {
    window.location.reload();
  }
}
