import { Component, OnInit, ChangeDetectionStrategy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { RegReportingGridComponent } from '../components/reg-reporting-grid/reg-reporting-grid.component';

@Component({
  selector: 'app-reg-entry',
  standalone: true,
  imports: [CommonModule, RegReportingGridComponent],
  template: `
    <div class="module-container">
      <header class="module-header">
        <div class="header-content">
          <h1>Regulatory Reporting</h1>
          <p class="subtitle">Compliance and regulatory filings</p>
        </div>
        <div class="header-meta">
          <span class="ag-version">AG Grid v31.0.0</span>
        </div>
      </header>
      
      <section class="module-content">
        <div class="content-header">
          <div class="tabs">
            <button class="tab" [class.active]="activeTab() === 'reports'" (click)="setActiveTab('reports')">Regulatory Reports</button>
            <button class="tab" [class.active]="activeTab() === 'submissions'" (click)="setActiveTab('submissions')">Submissions</button>
            <button class="tab" [class.active]="activeTab() === 'compliance'" (click)="setActiveTab('compliance')">Compliance</button>
          </div>
          <button class="btn btn-primary">+ New Report</button>
        </div>
        
        @if (activeTab() === 'reports') {
          <app-reg-reporting-grid></app-reg-reporting-grid>
        } @else {
          <div class="placeholder-content">
            <h3>{{ activeTab() | titlecase }}</h3>
            <p>Coming soon...</p>
          </div>
        }
      </section>
      
      <!-- Cross-Module Navigation -->
      <section class="quick-nav">
        <h3>Navigate to Other Modules</h3>
        <div class="nav-cards">
          @for (module of otherModules; track module.path) {
            <button class="nav-card" (click)="navigateTo(module.path)">
              <span class="nav-icon">{{ module.icon }}</span>
              <span class="nav-name">{{ module.name }}</span>
              <span class="nav-version">{{ module.agGrid }}</span>
            </button>
          }
        </div>
      </section>
    </div>
  `,
  styles: [`
    .module-container { display: flex; flex-direction: column; min-height: calc(100vh - 128px); background: #f8f9fa; }
    .module-header { display: flex; justify-content: space-between; align-items: center; padding: 24px; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; border-radius: 8px; margin-bottom: 24px; }
    .header-content h1 { margin: 0 0 4px 0; font-size: 1.75rem; }
    .subtitle { margin: 0; opacity: 0.8; }
    .ag-version { padding: 6px 12px; background: rgba(255,255,255,0.2); border-radius: 16px; font-size: 0.85rem; }
    .module-content { flex: 1; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .content-header { display: flex; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid #e5e7eb; }
    .tabs { display: flex; gap: 4px; }
    .tab { padding: 8px 16px; background: transparent; border: none; border-radius: 6px; font-weight: 500; color: #6b7280; cursor: pointer; }
    .tab:hover { background: #f3f4f6; }
    .tab.active { background: #2563eb; color: white; }
    .btn { padding: 8px 16px; border: none; border-radius: 6px; font-weight: 500; cursor: pointer; }
    .btn-primary { background: #2563eb; color: white; }
    .placeholder-content { padding: 48px; text-align: center; color: #6b7280; }
    
    .quick-nav {
      margin-top: 24px;
      padding: 24px;
      background: white;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .quick-nav h3 {
      margin: 0 0 16px 0;
      font-size: 1rem;
      color: #374151;
    }
    
    .nav-cards {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    
    .nav-card {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      background: #f3f4f6;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }
    
    .nav-card:hover {
      background: #e5e7eb;
      transform: translateY(-1px);
    }
    
    .nav-icon { font-size: 1.25rem; }
    .nav-name { font-weight: 500; color: #374151; }
    .nav-version { padding: 2px 6px; background: #dbeafe; color: #1d4ed8; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EntryComponent implements OnInit {
  activeTab = signal<'reports' | 'submissions' | 'compliance'>('reports');
  
  otherModules = [
    { path: '/financial-reporting', name: 'Financial', icon: '💰', agGrid: 'v30' },
    { path: '/expense-reporting', name: 'Expense', icon: '💳', agGrid: 'v31' },
    { path: '/tax-reporting', name: 'Tax', icon: '🧾', agGrid: 'v29' },
    { path: '/control-tower', name: 'Control Tower', icon: '🎯', agGrid: 'v31' }
  ];
  
  constructor(private router: Router) {}
  
  ngOnInit(): void { console.log('[RegReporting] Module loaded - AG Grid v31.0.0'); }
  setActiveTab(tab: 'reports' | 'submissions' | 'compliance'): void { this.activeTab.set(tab); }
  
  navigateTo(path: string): void {
    this.router.navigate([path]);
  }
}
