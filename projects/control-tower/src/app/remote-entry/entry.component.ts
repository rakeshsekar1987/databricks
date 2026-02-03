import { Component, OnInit, ChangeDetectionStrategy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { DashboardComponent } from '../components/dashboard/dashboard.component';

@Component({
  selector: 'app-control-entry',
  standalone: true,
  imports: [CommonModule, DashboardComponent],
  template: `
    <div class="module-container">
      <header class="module-header">
        <div class="header-content">
          <h1>Control Tower</h1>
          <p class="subtitle">Platform monitoring and management</p>
        </div>
        <div class="header-meta">
          <span class="ag-version">AG Grid v31.0.0</span>
        </div>
      </header>
      
      <section class="module-content">
        <div class="content-header">
          <div class="tabs">
            <button class="tab" [class.active]="activeTab() === 'dashboard'" (click)="setActiveTab('dashboard')">Dashboard</button>
            <button class="tab" [class.active]="activeTab() === 'modules'" (click)="setActiveTab('modules')">Modules</button>
            <button class="tab" [class.active]="activeTab() === 'health'" (click)="setActiveTab('health')">Health</button>
          </div>
        </div>
        
        @if (activeTab() === 'dashboard') {
          <app-dashboard></app-dashboard>
        } @else {
          <div class="placeholder-content">
            <h3>{{ activeTab() | titlecase }}</h3>
            <p>Coming soon...</p>
          </div>
        }
      </section>
      
      <!-- Quick Module Access -->
      <section class="quick-nav">
        <h3>Quick Access to Modules</h3>
        <div class="nav-cards">
          @for (module of allModules; track module.path) {
            <button class="nav-card" (click)="navigateTo(module.path)">
              <span class="nav-icon">{{ module.icon }}</span>
              <div class="nav-info">
                <span class="nav-name">{{ module.name }}</span>
                <span class="nav-desc">{{ module.description }}</span>
              </div>
              <span class="nav-version">{{ module.agGrid }}</span>
            </button>
          }
        </div>
      </section>
    </div>
  `,
  styles: [`
    .module-container { display: flex; flex-direction: column; min-height: calc(100vh - 128px); background: #f8f9fa; }
    .module-header { display: flex; justify-content: space-between; align-items: center; padding: 24px; background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; border-radius: 8px; margin-bottom: 24px; }
    .header-content h1 { margin: 0 0 4px 0; font-size: 1.75rem; }
    .subtitle { margin: 0; opacity: 0.8; }
    .ag-version { padding: 6px 12px; background: rgba(255,255,255,0.2); border-radius: 16px; font-size: 0.85rem; }
    .module-content { flex: 1; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .content-header { display: flex; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid #e5e7eb; }
    .tabs { display: flex; gap: 4px; }
    .tab { padding: 8px 16px; background: transparent; border: none; border-radius: 6px; font-weight: 500; color: #6b7280; cursor: pointer; }
    .tab:hover { background: #f3f4f6; }
    .tab.active { background: #dc2626; color: white; }
    .placeholder-content { padding: 48px; text-align: center; color: #6b7280; }
    
    .quick-nav { margin-top: 24px; padding: 24px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .quick-nav h3 { margin: 0 0 16px 0; font-size: 1rem; color: #374151; }
    .nav-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
    .nav-card { display: flex; align-items: center; gap: 12px; padding: 16px; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.2s; text-align: left; }
    .nav-card:hover { background: #e5e7eb; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .nav-icon { font-size: 2rem; }
    .nav-info { flex: 1; }
    .nav-name { display: block; font-weight: 600; color: #1f2937; margin-bottom: 2px; }
    .nav-desc { display: block; font-size: 0.8rem; color: #6b7280; }
    .nav-version { padding: 4px 8px; background: #fee2e2; color: #dc2626; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EntryComponent implements OnInit {
  activeTab = signal<'dashboard' | 'modules' | 'health'>('dashboard');
  
  allModules = [
    { path: '/reg-reporting', name: 'Regulatory Reporting', description: 'Compliance and regulatory filings', icon: '📋', agGrid: 'v31' },
    { path: '/financial-reporting', name: 'Financial Reporting', description: 'Financial statements and analysis', icon: '💰', agGrid: 'v30' },
    { path: '/expense-reporting', name: 'Expense Reporting', description: 'Track and manage expenses', icon: '💳', agGrid: 'v31' },
    { path: '/tax-reporting', name: 'Tax Reporting', description: 'Tax calculations and filing', icon: '🧾', agGrid: 'v29' }
  ];
  
  constructor(private router: Router) {}
  
  ngOnInit(): void { console.log('[ControlTower] Module loaded - AG Grid v31.0.0'); }
  setActiveTab(tab: 'dashboard' | 'modules' | 'health'): void { this.activeTab.set(tab); }
  
  navigateTo(path: string): void {
    this.router.navigate([path]);
  }
}
