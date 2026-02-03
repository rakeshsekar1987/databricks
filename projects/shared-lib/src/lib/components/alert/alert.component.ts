import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

export type AlertType = 'info' | 'success' | 'warning' | 'error';

/**
 * Motif-styled Alert Component
 * 
 * Displays contextual feedback messages with optional dismiss functionality.
 */
@Component({
  selector: 'lib-alert',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="alert" [class]="alertClasses" role="alert" [attr.aria-live]="ariaLive">
      <span class="alert-icon">{{ typeIcons[type] }}</span>
      <div class="alert-content">
        @if (title) {
          <strong class="alert-title">{{ title }}</strong>
        }
        <span class="alert-message"><ng-content></ng-content></span>
      </div>
      @if (dismissible) {
        <button class="alert-dismiss" (click)="onDismiss.emit()" aria-label="Dismiss">
          ✕
        </button>
      }
    </div>
  `,
  styles: [`
    .alert {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 12px 16px;
      border-radius: 6px;
      border-left: 4px solid;
    }
    
    .type-info { background: #e3f2fd; border-left-color: #2196f3; }
    .type-success { background: #e8f5e9; border-left-color: #4caf50; }
    .type-warning { background: #fff3e0; border-left-color: #ff9800; }
    .type-error { background: #ffebee; border-left-color: #f44336; }
    
    .alert-icon { font-size: 1.25rem; }
    
    .alert-content { flex: 1; }
    
    .alert-title {
      display: block;
      margin-bottom: 4px;
      font-weight: 600;
    }
    
    .alert-message { font-size: 0.9rem; }
    
    .alert-dismiss {
      background: transparent;
      border: none;
      font-size: 1rem;
      cursor: pointer;
      opacity: 0.6;
      transition: opacity 0.2s;
    }
    
    .alert-dismiss:hover { opacity: 1; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AlertComponent {
  @Input() type: AlertType = 'info';
  @Input() title?: string;
  @Input() dismissible = false;
  
  @Output() onDismiss = new EventEmitter<void>();
  
  readonly typeIcons: Record<AlertType, string> = {
    info: 'ℹ️',
    success: '✅',
    warning: '⚠️',
    error: '❌'
  };
  
  get alertClasses(): string {
    return `type-${this.type}`;
  }
  
  get ariaLive(): 'polite' | 'assertive' {
    return this.type === 'error' ? 'assertive' : 'polite';
  }
}
