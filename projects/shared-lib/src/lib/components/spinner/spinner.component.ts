import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Motif-styled Spinner Component
 * 
 * Loading indicator with customizable size and message.
 */
@Component({
  selector: 'lib-spinner',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="spinner-container" [class.overlay]="overlay" role="status" aria-live="polite">
      <div class="spinner" [class]="sizeClass"></div>
      @if (message) {
        <p class="spinner-message">{{ message }}</p>
      }
      <span class="sr-only">Loading...</span>
    </div>
  `,
  styles: [`
    .spinner-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
    }
    
    .spinner-container.overlay {
      position: absolute;
      inset: 0;
      background: rgba(255, 255, 255, 0.9);
      z-index: 100;
    }
    
    .spinner {
      border: 3px solid var(--motif-border-color, #e0e0e0);
      border-top-color: var(--motif-primary, #1976d2);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    
    .size-small { width: 24px; height: 24px; border-width: 2px; }
    .size-medium { width: 40px; height: 40px; }
    .size-large { width: 56px; height: 56px; border-width: 4px; }
    
    .spinner-message {
      margin: 0;
      font-size: 0.9rem;
      color: var(--motif-text-secondary, #666);
    }
    
    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      border: 0;
    }
    
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SpinnerComponent {
  @Input() size: 'small' | 'medium' | 'large' = 'medium';
  @Input() message?: string;
  @Input() overlay = false;
  
  get sizeClass(): string {
    return `size-${this.size}`;
  }
}
