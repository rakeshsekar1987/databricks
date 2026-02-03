import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';

/**
 * Header Component
 * 
 * Provides the main navigation header
 */
@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  template: `
    <header class="header" role="banner">
      <div class="header-brand">
        <a routerLink="/" class="brand-link">
          <span class="brand-icon">📊</span>
          <span class="brand-text">UI Platform</span>
        </a>
        <span class="brand-badge">Module Federation POC</span>
      </div>
      
      <nav class="header-nav" role="navigation" aria-label="Main navigation">
        <a routerLink="/" 
           routerLinkActive="active" 
           [routerLinkActiveOptions]="{exact: true}"
           class="nav-link">
          Home
        </a>
        <a routerLink="/reg-reporting" 
           routerLinkActive="active" 
           class="nav-link">
          Regulatory
        </a>
        <a routerLink="/financial-reporting" 
           routerLinkActive="active" 
           class="nav-link">
          Financial
        </a>
        <a routerLink="/expense-reporting" 
           routerLinkActive="active" 
           class="nav-link">
          Expense
        </a>
        <a routerLink="/tax-reporting" 
           routerLinkActive="active" 
           class="nav-link">
          Tax
        </a>
        <a routerLink="/control-tower" 
           routerLinkActive="active" 
           class="nav-link">
          Control Tower
        </a>
      </nav>
      
      <div class="header-actions">
        <span class="user-info">
          <span class="user-avatar">DU</span>
          <span class="user-name">Demo User</span>
        </span>
      </div>
    </header>
  `,
  styles: [`
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      height: 64px;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: white;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      z-index: 1000;
    }
    
    .header-brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    
    .brand-link {
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
      color: white;
      font-size: 1.25rem;
      font-weight: 600;
    }
    
    .brand-icon {
      font-size: 1.5rem;
    }
    
    .brand-badge {
      padding: 2px 8px;
      font-size: 0.7rem;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    .header-nav {
      display: flex;
      gap: 8px;
    }
    
    .nav-link {
      padding: 8px 16px;
      color: rgba(255, 255, 255, 0.8);
      text-decoration: none;
      border-radius: 6px;
      transition: all 0.2s ease;
      font-weight: 500;
    }
    
    .nav-link:hover {
      background: rgba(255, 255, 255, 0.1);
      color: white;
    }
    
    .nav-link.active {
      background: rgba(255, 255, 255, 0.2);
      color: white;
    }
    
    .header-actions {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    
    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 12px 4px 4px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 24px;
    }
    
    .user-avatar {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8rem;
      font-weight: 600;
    }
    
    .user-name {
      font-size: 0.9rem;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HeaderComponent {}
