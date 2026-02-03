import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="app-container">
      <!-- Header -->
      <header class="header">
        <div class="brand">
          <span class="brand-icon">📊</span>
          <span class="brand-text">UI Platform</span>
          <span class="brand-badge">Module Federation POC</span>
        </div>
        
        <nav class="nav">
          <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}">Home</a>
          <a routerLink="/reg-reporting" routerLinkActive="active">Regulatory</a>
          <a routerLink="/financial-reporting" routerLinkActive="active">Financial</a>
          <a routerLink="/expense-reporting" routerLinkActive="active">Expense</a>
          <a routerLink="/tax-reporting" routerLinkActive="active">Tax</a>
          <a routerLink="/control-tower" routerLinkActive="active">Control Tower</a>
        </nav>
        
        <div class="user">
          <span class="avatar">DU</span>
          <span>Demo User</span>
        </div>
      </header>
      
      <!-- Main Content -->
      <main class="main">
        <router-outlet></router-outlet>
      </main>
      
      <!-- Footer -->
      <footer class="footer">
        <span>Angular Module Federation POC</span>
        <span>AG Grid Versions: v29, v30, v31</span>
      </footer>
    </div>
  `,
  styles: [`
    .app-container {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      background: #f5f5f5;
    }
    
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      height: 64px;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: white;
    }
    
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    
    .brand-icon { font-size: 1.5rem; }
    .brand-text { font-size: 1.25rem; font-weight: 600; }
    .brand-badge {
      padding: 2px 8px;
      font-size: 0.7rem;
      background: rgba(255,255,255,0.2);
      border-radius: 4px;
    }
    
    .nav {
      display: flex;
      gap: 8px;
    }
    
    .nav a {
      padding: 8px 16px;
      color: rgba(255,255,255,0.8);
      text-decoration: none;
      border-radius: 6px;
      transition: all 0.2s;
    }
    
    .nav a:hover {
      background: rgba(255,255,255,0.1);
      color: white;
    }
    
    .nav a.active {
      background: rgba(255,255,255,0.2);
      color: white;
    }
    
    .user {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 12px 4px 4px;
      background: rgba(255,255,255,0.1);
      border-radius: 24px;
    }
    
    .avatar {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8rem;
      font-weight: 600;
    }
    
    .main {
      flex: 1;
      padding: 24px;
      overflow-y: auto;
    }
    
    .footer {
      display: flex;
      justify-content: space-between;
      padding: 16px 24px;
      background: #1a1a2e;
      color: rgba(255,255,255,0.7);
      font-size: 0.85rem;
    }
  `]
})
export class AppComponent {
  constructor() {
    console.log('[Shell] AppComponent initialized');
  }
}
