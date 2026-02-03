import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonComponent } from '../button/button.component';

/**
 * Motif-styled Modal Component
 * 
 * Overlay dialog for focused interactions.
 */
@Component({
  selector: 'lib-modal',
  standalone: true,
  imports: [CommonModule, ButtonComponent],
  template: `
    @if (isOpen) {
      <div class="modal-overlay" (click)="onOverlayClick($event)" role="dialog" [attr.aria-modal]="true" [attr.aria-labelledby]="title ? 'modal-title' : null">
        <div class="modal-container" [class]="sizeClass" (click)="$event.stopPropagation()">
          <header class="modal-header">
            @if (title) {
              <h2 id="modal-title" class="modal-title">{{ title }}</h2>
            }
            @if (closable) {
              <button class="modal-close" (click)="close.emit()" aria-label="Close">✕</button>
            }
          </header>
          
          <div class="modal-body">
            <ng-content></ng-content>
          </div>
          
          @if (showFooter) {
            <footer class="modal-footer">
              <ng-content select="[modal-footer]"></ng-content>
            </footer>
          }
        </div>
      </div>
    }
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      animation: fadeIn 0.2s ease;
    }
    
    .modal-container {
      background: white;
      border-radius: 12px;
      box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      animation: slideUp 0.2s ease;
    }
    
    .size-small { width: 400px; }
    .size-medium { width: 560px; }
    .size-large { width: 720px; }
    .size-full { width: 90vw; max-width: 1200px; }
    
    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 24px;
      border-bottom: 1px solid var(--motif-border-color, #e0e0e0);
    }
    
    .modal-title {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 600;
    }
    
    .modal-close {
      background: transparent;
      border: none;
      font-size: 1.25rem;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
      transition: background 0.2s;
    }
    
    .modal-close:hover { background: #f5f5f5; }
    
    .modal-body {
      padding: 24px;
      overflow-y: auto;
      flex: 1;
    }
    
    .modal-footer {
      padding: 16px 24px;
      border-top: 1px solid var(--motif-border-color, #e0e0e0);
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
    
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    
    @keyframes slideUp {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ModalComponent {
  @Input() isOpen = false;
  @Input() title?: string;
  @Input() size: 'small' | 'medium' | 'large' | 'full' = 'medium';
  @Input() closable = true;
  @Input() closeOnOverlay = true;
  @Input() showFooter = false;
  
  @Output() close = new EventEmitter<void>();
  
  get sizeClass(): string {
    return `size-${this.size}`;
  }
  
  onOverlayClick(event: MouseEvent): void {
    if (this.closeOnOverlay && event.target === event.currentTarget) {
      this.close.emit();
    }
  }
}
