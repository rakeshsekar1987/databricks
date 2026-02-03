import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="home">
      <h1>UI Module Federation Platform</h1>
      <p class="subtitle">Independent micro-frontends with separate AG Grid versions</p>
      
      <div class="features">
        <div class="feature-card">
          <span class="icon">🏗️</span>
          <h3>Module Federation</h3>
          <p>Dynamic runtime loading of independent modules</p>
        </div>
        <div class="feature-card">
          <span class="icon">📊</span>
          <h3>AG Grid Versioning</h3>
          <p>Different AG Grid versions per module (v29, v30, v31)</p>
        </div>
        <div class="feature-card">
          <span class="icon">🚀</span>
          <h3>Independent Deployment</h3>
          <p>Deploy modules independently without affecting others</p>
        </div>
        <div class="feature-card">
          <span class="icon">🔗</span>
          <h3>Shared Libraries</h3>
          <p>Common components shared across all modules</p>
        </div>
      </div>
      
      <h2>Available Modules</h2>
      <div class="modules">
        <a routerLink="/reg-reporting" class="module-card">
          <span class="module-icon">📋</span>
          <div class="module-info">
            <h3>Regulatory Reporting</h3>
            <span class="badge">AG Grid v31</span>
          </div>
        </a>
        <a routerLink="/financial-reporting" class="module-card">
          <span class="module-icon">💰</span>
          <div class="module-info">
            <h3>Financial Reporting</h3>
            <span class="badge">AG Grid v30</span>
          </div>
        </a>
        <a routerLink="/expense-reporting" class="module-card">
          <span class="module-icon">💳</span>
          <div class="module-info">
            <h3>Expense Reporting</h3>
            <span class="badge">AG Grid v31</span>
          </div>
        </a>
        <a routerLink="/tax-reporting" class="module-card">
          <span class="module-icon">🧾</span>
          <div class="module-info">
            <h3>Tax Reporting</h3>
            <span class="badge">AG Grid v29</span>
          </div>
        </a>
        <a routerLink="/control-tower" class="module-card">
          <span class="module-icon">🎯</span>
          <div class="module-info">
            <h3>Control Tower</h3>
            <span class="badge">AG Grid v31</span>
          </div>
        </a>
      </div>
    </div>
  `,
  styles: [`
    .home {
      max-width: 1200px;
      margin: 0 auto;
    }
    
    h1 {
      font-size: 2.5rem;
      color: #1a1a2e;
      margin-bottom: 8px;
    }
    
    .subtitle {
      font-size: 1.2rem;
      color: #666;
      margin-bottom: 32px;
    }
    
    h2 {
      font-size: 1.5rem;
      margin: 32px 0 16px;
      color: #1a1a2e;
    }
    
    .features {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin-bottom: 32px;
    }
    
    .feature-card {
      background: white;
      padding: 24px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .feature-card .icon {
      font-size: 2rem;
      display: block;
      margin-bottom: 12px;
    }
    
    .feature-card h3 {
      margin: 0 0 8px;
      color: #1a1a2e;
    }
    
    .feature-card p {
      margin: 0;
      color: #666;
      font-size: 0.9rem;
    }
    
    .modules {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 20px;
    }
    
    .module-card {
      display: flex;
      align-items: center;
      gap: 16px;
      background: white;
      padding: 20px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      text-decoration: none;
      color: inherit;
      transition: transform 0.2s, box-shadow 0.2s;
      border: 2px solid transparent;
    }
    
    .module-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
      border-color: #1976d2;
    }
    
    .module-icon {
      font-size: 2.5rem;
    }
    
    .module-info h3 {
      margin: 0 0 4px;
      color: #1a1a2e;
    }
    
    .badge {
      display: inline-block;
      padding: 2px 8px;
      font-size: 0.75rem;
      background: #e8f5e9;
      color: #2e7d32;
      border-radius: 4px;
      font-weight: 600;
    }
  `]
})
export class HomeComponent {
  constructor() {
    console.log('[Home] Component initialized');
  }
}
