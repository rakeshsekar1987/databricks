import { Component, OnInit, ChangeDetectionStrategy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ModuleRegistryService, ModuleConfig } from '../../core/services/module-registry.service';

/**
 * Home Component
 * 
 * Landing page displaying:
 * - Module overview cards
 * - Quick navigation
 * - Platform information
 */
@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="home-container">
      <header class="home-header">
        <h1>UI Module Federation Platform</h1>
        <p class="subtitle">
          Independent micro-frontends with separate AG Grid versions
        </p>
      </header>
      
      <section class="architecture-info">
        <div class="info-card">
          <div class="info-icon">🏗️</div>
          <div class="info-content">
            <h3>Module Federation</h3>
            <p>Dynamic runtime loading of independent modules</p>
          </div>
        </div>
        <div class="info-card">
          <div class="info-icon">🎨</div>
          <div class="info-content">
            <h3>Motif Design System</h3>
            <p>Shared component library across all modules</p>
          </div>
        </div>
        <div class="info-card">
          <div class="info-icon">📊</div>
          <div class="info-content">
            <h3>AG Grid Versioning</h3>
            <p>Different AG Grid versions per module (v29, v30, v31)</p>
          </div>
        </div>
        <div class="info-card">
          <div class="info-icon">🚀</div>
          <div class="info-content">
            <h3>Independent Deployment</h3>
            <p>Deploy modules independently without affecting others</p>
          </div>
        </div>
      </section>
      
      <section class="modules-section">
        <h2>Available Modules</h2>
        <div class="modules-grid">
          @for (module of modules; track module.name) {
            <a [routerLink]="'/' + module.name.replace(/([A-Z])/g, '-$1').toLowerCase().substring(1)" 
               class="module-card">
              <div class="module-header">
                <span class="module-icon">{{ getModuleIcon(module.name) }}</span>
                <span class="ag-version-badge">AG Grid {{ module.agGridVersion }}</span>
              </div>
              <h3 class="module-title">{{ module.displayName }}</h3>
              <p class="module-description">{{ module.description }}</p>
              <div class="module-footer">
                <span class="status-indicator" [class]="module.status">
                  {{ module.status }}
                </span>
                <span class="module-link">Open →</span>
              </div>
            </a>
          }
        </div>
      </section>
      
      <section class="quick-start">
        <h2>Quick Start</h2>
        <div class="code-block">
          <pre><code># Start all modules
npm run start:all

# Start individual modules
npm run start:shell        # Port 4200
npm run start:reg-reporting    # Port 4201
npm run start:financial-reporting # Port 4202
npm run start:tax-reporting    # Port 4204</code></pre>
        </div>
      </section>
    </div>
  `,
  styles: [`
    .home-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }
    
    .home-header {
      text-align: center;
      margin-bottom: 48px;
    }
    
    .home-header h1 {
      font-size: 2.5rem;
      color: #1a1a2e;
      margin-bottom: 16px;
    }
    
    .subtitle {
      font-size: 1.25rem;
      color: #666;
    }
    
    .architecture-info {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 24px;
      margin-bottom: 48px;
    }
    
    .info-card {
      display: flex;
      gap: 16px;
      padding: 24px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .info-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    }
    
    .info-icon {
      font-size: 2rem;
    }
    
    .info-content h3 {
      margin: 0 0 8px 0;
      font-size: 1.1rem;
      color: #1a1a2e;
    }
    
    .info-content p {
      margin: 0;
      font-size: 0.9rem;
      color: #666;
    }
    
    .modules-section h2,
    .quick-start h2 {
      margin-bottom: 24px;
      font-size: 1.5rem;
      color: #1a1a2e;
    }
    
    .modules-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 24px;
      margin-bottom: 48px;
    }
    
    .module-card {
      display: flex;
      flex-direction: column;
      padding: 24px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      text-decoration: none;
      color: inherit;
      transition: transform 0.2s, box-shadow 0.2s;
      border: 2px solid transparent;
    }
    
    .module-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
      border-color: #1976d2;
    }
    
    .module-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    
    .module-icon {
      font-size: 2rem;
    }
    
    .ag-version-badge {
      padding: 4px 8px;
      font-size: 0.7rem;
      font-weight: 600;
      background: #e8f5e9;
      color: #2e7d32;
      border-radius: 4px;
    }
    
    .module-title {
      margin: 0 0 8px 0;
      font-size: 1.25rem;
      color: #1a1a2e;
    }
    
    .module-description {
      flex: 1;
      margin: 0 0 16px 0;
      font-size: 0.9rem;
      color: #666;
    }
    
    .module-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .status-indicator {
      padding: 4px 8px;
      font-size: 0.7rem;
      font-weight: 500;
      border-radius: 4px;
      text-transform: uppercase;
    }
    
    .status-indicator.online {
      background: #e8f5e9;
      color: #2e7d32;
    }
    
    .status-indicator.offline {
      background: #ffebee;
      color: #c62828;
    }
    
    .status-indicator.unknown {
      background: #fff3e0;
      color: #ef6c00;
    }
    
    .module-link {
      color: #1976d2;
      font-weight: 500;
    }
    
    .code-block {
      background: #1a1a2e;
      border-radius: 8px;
      padding: 24px;
      overflow-x: auto;
    }
    
    .code-block pre {
      margin: 0;
    }
    
    .code-block code {
      color: #e0e0e0;
      font-family: 'Fira Code', 'Consolas', monospace;
      font-size: 0.9rem;
      line-height: 1.6;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HomeComponent implements OnInit {
  private readonly moduleRegistry = inject(ModuleRegistryService);
  
  modules: ModuleConfig[] = [];
  
  private readonly moduleIcons: Record<string, string> = {
    regReporting: '📋',
    financialReporting: '💰',
    expenseReporting: '💳',
    taxReporting: '🧾',
    controlTower: '🎯'
  };
  
  ngOnInit(): void {
    this.modules = this.moduleRegistry.getAllModules();
  }
  
  getModuleIcon(moduleName: string): string {
    return this.moduleIcons[moduleName] || '📦';
  }
}
