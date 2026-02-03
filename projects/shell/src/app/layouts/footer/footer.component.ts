import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Footer Component
 * 
 * Displays application footer with:
 * - Version information
 * - Environment indicator
 * - Copyright notice
 */
@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <footer class="footer" role="contentinfo">
      <div class="footer-content">
        <div class="footer-left">
          <span class="footer-brand">UI Module Federation Platform</span>
          <span class="footer-separator">|</span>
          <span class="footer-version">v1.0.0</span>
        </div>
        
        <div class="footer-center">
          <span class="env-badge" [class]="environment">
            {{ environment | uppercase }}
          </span>
        </div>
        
        <div class="footer-right">
          <span class="footer-tech">Angular 17 + Module Federation</span>
          <span class="footer-separator">|</span>
          <span class="footer-copyright">© {{ currentYear }}</span>
        </div>
      </div>
    </footer>
  `,
  styles: [`
    .footer {
      padding: 12px 24px;
      background: #1a1a2e;
      color: rgba(255, 255, 255, 0.7);
      font-size: 0.8rem;
    }
    
    .footer-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .footer-left,
    .footer-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    .footer-separator {
      color: rgba(255, 255, 255, 0.3);
    }
    
    .footer-brand {
      font-weight: 500;
      color: white;
    }
    
    .env-badge {
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    .env-badge.development {
      background: #ff9800;
      color: #000;
    }
    
    .env-badge.staging {
      background: #2196f3;
      color: #fff;
    }
    
    .env-badge.production {
      background: #4caf50;
      color: #fff;
    }
    
    .footer-tech {
      color: rgba(255, 255, 255, 0.5);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FooterComponent {
  environment = 'development';
  currentYear = new Date().getFullYear();
}
