import { Component, ChangeDetectionStrategy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';

interface NavItem {
  path: string;
  label: string;
  icon: string;
  agGridVersion?: string;
  description?: string;
}

/**
 * Sidebar Component
 * 
 * Provides module navigation with:
 * - Module links with icons
 * - AG Grid version indicators
 * - Collapsible functionality
 */
@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  template: `
    <aside class="sidebar" [class.collapsed]="isCollapsed()" role="complementary">
      <button 
        class="collapse-btn" 
        (click)="toggleCollapse()"
        [attr.aria-expanded]="!isCollapsed()"
        aria-label="Toggle sidebar">
        {{ isCollapsed() ? '→' : '←' }}
      </button>
      
      <nav class="sidebar-nav" role="navigation" aria-label="Module navigation">
        <div class="nav-section">
          <span class="nav-section-title" *ngIf="!isCollapsed()">Modules</span>
          
          @for (item of navItems; track item.path) {
            <a 
              [routerLink]="item.path" 
              routerLinkActive="active"
              class="nav-item"
              [title]="item.label">
              <span class="nav-icon">{{ item.icon }}</span>
              @if (!isCollapsed()) {
                <span class="nav-label">{{ item.label }}</span>
                @if (item.agGridVersion) {
                  <span class="version-badge">{{ item.agGridVersion }}</span>
                }
              }
            </a>
          }
        </div>
        
        <div class="nav-section" *ngIf="!isCollapsed()">
          <span class="nav-section-title">Settings</span>
          <a routerLink="/settings" class="nav-item">
            <span class="nav-icon">⚙️</span>
            <span class="nav-label">Configuration</span>
          </a>
          <a routerLink="/help" class="nav-item">
            <span class="nav-icon">❓</span>
            <span class="nav-label">Help & Support</span>
          </a>
        </div>
      </nav>
      
      @if (!isCollapsed()) {
        <div class="sidebar-footer">
          <div class="module-info">
            <span class="info-label">Architecture</span>
            <span class="info-value">Module Federation</span>
          </div>
          <div class="module-info">
            <span class="info-label">Framework</span>
            <span class="info-value">Angular 17</span>
          </div>
        </div>
      }
    </aside>
  `,
  styles: [`
    .sidebar {
      width: 260px;
      min-width: 260px;
      background: white;
      border-right: 1px solid #e0e0e0;
      display: flex;
      flex-direction: column;
      transition: width 0.3s ease, min-width 0.3s ease;
      position: relative;
    }
    
    .sidebar.collapsed {
      width: 64px;
      min-width: 64px;
    }
    
    .collapse-btn {
      position: absolute;
      top: 16px;
      right: -12px;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: white;
      border: 1px solid #e0e0e0;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      z-index: 10;
      transition: background 0.2s;
    }
    
    .collapse-btn:hover {
      background: #f5f5f5;
    }
    
    .sidebar-nav {
      flex: 1;
      padding: 16px 0;
      overflow-y: auto;
    }
    
    .nav-section {
      margin-bottom: 24px;
    }
    
    .nav-section-title {
      display: block;
      padding: 8px 20px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #888;
    }
    
    .nav-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 20px;
      text-decoration: none;
      color: #333;
      transition: all 0.2s ease;
      border-left: 3px solid transparent;
    }
    
    .sidebar.collapsed .nav-item {
      justify-content: center;
      padding: 12px;
    }
    
    .nav-item:hover {
      background: #f5f5f5;
    }
    
    .nav-item.active {
      background: #e3f2fd;
      border-left-color: #1976d2;
      color: #1976d2;
    }
    
    .nav-icon {
      font-size: 1.25rem;
      width: 24px;
      text-align: center;
    }
    
    .nav-label {
      flex: 1;
      font-weight: 500;
    }
    
    .version-badge {
      font-size: 0.65rem;
      padding: 2px 6px;
      background: #e8f5e9;
      color: #2e7d32;
      border-radius: 4px;
      font-weight: 600;
    }
    
    .sidebar-footer {
      padding: 16px 20px;
      border-top: 1px solid #e0e0e0;
      background: #fafafa;
    }
    
    .module-info {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
      font-size: 0.8rem;
    }
    
    .info-label {
      color: #888;
    }
    
    .info-value {
      font-weight: 500;
      color: #333;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SidebarComponent {
  isCollapsed = signal(false);
  
  navItems: NavItem[] = [
    {
      path: '/reg-reporting',
      label: 'Regulatory Reporting',
      icon: '📋',
      agGridVersion: 'v31',
      description: 'Regulatory compliance reports'
    },
    {
      path: '/financial-reporting',
      label: 'Financial Reporting',
      icon: '💰',
      agGridVersion: 'v30',
      description: 'Financial statements and reports'
    },
    {
      path: '/expense-reporting',
      label: 'Expense Reporting',
      icon: '💳',
      agGridVersion: 'v31',
      description: 'Expense management'
    },
    {
      path: '/tax-reporting',
      label: 'Tax Reporting',
      icon: '🧾',
      agGridVersion: 'v29',
      description: 'Tax calculations and filing'
    },
    {
      path: '/control-tower',
      label: 'Control Tower',
      icon: '🎯',
      agGridVersion: 'v31',
      description: 'Dashboard and monitoring'
    }
  ];
  
  toggleCollapse(): void {
    this.isCollapsed.update(value => !value);
  }
}
