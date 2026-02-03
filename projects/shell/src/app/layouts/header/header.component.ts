import { Component, ChangeDetectionStrategy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';

/**
 * Header Component
 * 
 * Provides the main navigation header with:
 * - Application branding
 * - Quick navigation links
 * - User profile with logout
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
        <span class="brand-badge">Module Federation</span>
      </div>
      
      @if (authService.isAuthenticated()) {
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
          <a routerLink="/tax-reporting" 
             routerLinkActive="active" 
             class="nav-link">
            Tax
          </a>
        </nav>
        
        <div class="header-actions">
          <button class="action-button" aria-label="Notifications">
            🔔
          </button>
          <button class="action-button" aria-label="Settings">
            ⚙️
          </button>
          
          <div class="user-profile" (click)="toggleDropdown()">
            <span class="user-avatar">{{ getUserInitials() }}</span>
            <span class="user-name">{{ authService.currentUser()?.name }}</span>
            <span class="dropdown-arrow">▼</span>
            
            @if (showDropdown()) {
              <div class="dropdown-menu">
                <div class="dropdown-header">
                  <span class="user-email">{{ authService.currentUser()?.email }}</span>
                  <span class="user-role">{{ authService.currentUser()?.title || 'User' }}</span>
                </div>
                <div class="dropdown-divider"></div>
                <a class="dropdown-item" routerLink="/profile">
                  👤 Profile
                </a>
                <a class="dropdown-item" routerLink="/settings">
                  ⚙️ Settings
                </a>
                <div class="dropdown-divider"></div>
                <button class="dropdown-item logout" (click)="logout()">
                  🚪 Sign Out
                </button>
              </div>
            }
          </div>
        </div>
      } @else {
        <div class="header-actions">
          <a routerLink="/login" class="login-link">Sign In</a>
        </div>
      }
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
    
    .action-button {
      background: transparent;
      border: none;
      cursor: pointer;
      font-size: 1.25rem;
      padding: 8px;
      border-radius: 50%;
      transition: background 0.2s;
    }
    
    .action-button:hover {
      background: rgba(255, 255, 255, 0.1);
    }
    
    .user-profile {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 12px 4px 4px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 24px;
      cursor: pointer;
      position: relative;
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
    
    .dropdown-arrow {
      font-size: 0.6rem;
      opacity: 0.7;
    }
    
    .dropdown-menu {
      position: absolute;
      top: 100%;
      right: 0;
      margin-top: 8px;
      width: 240px;
      background: white;
      border-radius: 8px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
      overflow: hidden;
      z-index: 1000;
    }
    
    .dropdown-header {
      padding: 16px;
      background: #f8f9fa;
    }
    
    .user-email {
      display: block;
      font-size: 0.9rem;
      color: #333;
      font-weight: 500;
    }
    
    .user-role {
      display: block;
      font-size: 0.8rem;
      color: #666;
      margin-top: 4px;
    }
    
    .dropdown-divider {
      height: 1px;
      background: #e0e0e0;
    }
    
    .dropdown-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      color: #333;
      text-decoration: none;
      font-size: 0.9rem;
      border: none;
      background: none;
      width: 100%;
      text-align: left;
      cursor: pointer;
      transition: background 0.2s;
    }
    
    .dropdown-item:hover {
      background: #f5f5f5;
    }
    
    .dropdown-item.logout {
      color: #dc2626;
    }
    
    .login-link {
      padding: 8px 20px;
      background: rgba(255, 255, 255, 0.2);
      color: white;
      text-decoration: none;
      border-radius: 6px;
      font-weight: 500;
      transition: background 0.2s;
    }
    
    .login-link:hover {
      background: rgba(255, 255, 255, 0.3);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HeaderComponent {
  readonly authService = inject(AuthService);
  showDropdown = signal(false);
  
  getUserInitials(): string {
    const user = this.authService.currentUser();
    if (!user) return '?';
    return `${user.firstName?.charAt(0) || ''}${user.lastName?.charAt(0) || ''}`.toUpperCase();
  }
  
  toggleDropdown(): void {
    this.showDropdown.update(v => !v);
  }
  
  logout(): void {
    this.showDropdown.set(false);
    this.authService.logout();
  }
}
