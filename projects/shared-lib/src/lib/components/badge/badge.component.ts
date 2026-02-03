import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

export type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info';

/**
 * Motif-styled Badge Component
 * 
 * Small status descriptor for UI elements.
 */
@Component({
  selector: 'lib-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span class="badge" [class]="badgeClasses">
      <ng-content></ng-content>
    </span>
  `,
  styles: [`
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      font-size: 0.75rem;
      font-weight: 600;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    .variant-default { background: #e0e0e0; color: #424242; }
    .variant-primary { background: #e3f2fd; color: #1565c0; }
    .variant-success { background: #e8f5e9; color: #2e7d32; }
    .variant-warning { background: #fff3e0; color: #ef6c00; }
    .variant-error { background: #ffebee; color: #c62828; }
    .variant-info { background: #e1f5fe; color: #0277bd; }
    
    .size-small { padding: 1px 6px; font-size: 0.65rem; }
    .size-large { padding: 4px 12px; font-size: 0.85rem; }
    
    .rounded { border-radius: 16px; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class BadgeComponent {
  @Input() variant: BadgeVariant = 'default';
  @Input() size: 'small' | 'medium' | 'large' = 'medium';
  @Input() rounded = false;
  
  get badgeClasses(): string {
    return [
      `variant-${this.variant}`,
      `size-${this.size}`,
      this.rounded ? 'rounded' : ''
    ].filter(Boolean).join(' ');
  }
}
