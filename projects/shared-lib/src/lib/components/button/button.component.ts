import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

export type ButtonVariant = 'primary' | 'secondary' | 'tertiary' | 'danger' | 'success';
export type ButtonSize = 'small' | 'medium' | 'large';

/**
 * Motif-styled Button Component
 * 
 * A reusable button component following Motif design patterns.
 * Supports multiple variants, sizes, and states.
 */
@Component({
  selector: 'lib-button',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button
      [type]="type"
      [class]="buttonClasses"
      [disabled]="disabled || loading"
      (click)="onClick.emit($event)"
      [attr.aria-label]="ariaLabel"
      [attr.aria-busy]="loading">
      @if (loading) {
        <span class="spinner"></span>
      }
      @if (icon && iconPosition === 'left') {
        <span class="icon">{{ icon }}</span>
      }
      <span class="label"><ng-content></ng-content></span>
      @if (icon && iconPosition === 'right') {
        <span class="icon">{{ icon }}</span>
      }
    </button>
  `,
  styles: [`
    button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-family: inherit;
      font-weight: 500;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    
    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    
    /* Sizes */
    .size-small { padding: 6px 12px; font-size: 0.8rem; }
    .size-medium { padding: 10px 20px; font-size: 0.9rem; }
    .size-large { padding: 14px 28px; font-size: 1rem; }
    
    /* Variants */
    .variant-primary { background: var(--motif-primary, #1976d2); color: white; }
    .variant-primary:hover:not(:disabled) { background: var(--motif-primary-dark, #1565c0); }
    
    .variant-secondary { background: transparent; color: var(--motif-primary, #1976d2); border: 1px solid var(--motif-primary, #1976d2); }
    .variant-secondary:hover:not(:disabled) { background: rgba(25, 118, 210, 0.08); }
    
    .variant-tertiary { background: transparent; color: var(--motif-text-primary, #333); }
    .variant-tertiary:hover:not(:disabled) { background: rgba(0, 0, 0, 0.04); }
    
    .variant-danger { background: var(--motif-error, #f44336); color: white; }
    .variant-danger:hover:not(:disabled) { background: #d32f2f; }
    
    .variant-success { background: var(--motif-success, #4caf50); color: white; }
    .variant-success:hover:not(:disabled) { background: #388e3c; }
    
    .full-width { width: 100%; }
    
    .spinner {
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ButtonComponent {
  @Input() variant: ButtonVariant = 'primary';
  @Input() size: ButtonSize = 'medium';
  @Input() type: 'button' | 'submit' | 'reset' = 'button';
  @Input() disabled = false;
  @Input() loading = false;
  @Input() fullWidth = false;
  @Input() icon?: string;
  @Input() iconPosition: 'left' | 'right' = 'left';
  @Input() ariaLabel?: string;
  
  @Output() onClick = new EventEmitter<MouseEvent>();
  
  get buttonClasses(): string {
    return [
      `variant-${this.variant}`,
      `size-${this.size}`,
      this.fullWidth ? 'full-width' : ''
    ].filter(Boolean).join(' ');
  }
}
