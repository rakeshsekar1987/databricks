import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Motif-styled Card Component
 * 
 * A container component with optional header, body, and footer sections.
 */
@Component({
  selector: 'lib-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <article class="card" [class.elevated]="elevated" [class.bordered]="bordered">
      @if (title || showHeader) {
        <header class="card-header">
          @if (title) {
            <h3 class="card-title">{{ title }}</h3>
          }
          @if (subtitle) {
            <p class="card-subtitle">{{ subtitle }}</p>
          }
          <div class="card-actions">
            <ng-content select="[card-actions]"></ng-content>
          </div>
        </header>
      }
      
      <div class="card-body" [class.no-padding]="noPadding">
        <ng-content></ng-content>
      </div>
      
      @if (showFooter) {
        <footer class="card-footer">
          <ng-content select="[card-footer]"></ng-content>
        </footer>
      }
    </article>
  `,
  styles: [`
    .card {
      background: white;
      border-radius: 8px;
      overflow: hidden;
    }
    
    .card.elevated {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .card.bordered {
      border: 1px solid var(--motif-border-color, #e0e0e0);
    }
    
    .card-header {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 16px;
      padding: 16px 20px;
      border-bottom: 1px solid var(--motif-border-color, #e0e0e0);
    }
    
    .card-title {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--motif-text-primary, #212121);
    }
    
    .card-subtitle {
      margin: 0;
      font-size: 0.9rem;
      color: var(--motif-text-secondary, #666);
    }
    
    .card-actions {
      margin-left: auto;
    }
    
    .card-body {
      padding: 20px;
    }
    
    .card-body.no-padding {
      padding: 0;
    }
    
    .card-footer {
      padding: 16px 20px;
      border-top: 1px solid var(--motif-border-color, #e0e0e0);
      background: var(--motif-bg-tertiary, #fafafa);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CardComponent {
  @Input() title?: string;
  @Input() subtitle?: string;
  @Input() elevated = true;
  @Input() bordered = false;
  @Input() noPadding = false;
  @Input() showHeader = false;
  @Input() showFooter = false;
}
