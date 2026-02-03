import { Component, OnInit, ChangeDetectionStrategy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ExpenseGridComponent } from '../components/expense-grid/expense-grid.component';

@Component({
  selector: 'app-expense-entry',
  standalone: true,
  imports: [CommonModule, ExpenseGridComponent],
  template: `
    <div class="module-container">
      <header class="module-header">
        <div class="header-content">
          <h1>Expense Reporting</h1>
          <p class="subtitle">Track and manage expenses</p>
        </div>
        <div class="header-meta">
          <span class="ag-version">AG Grid v31.0.0</span>
        </div>
      </header>
      
      <section class="module-content">
        <div class="content-header">
          <div class="tabs">
            <button class="tab" [class.active]="activeTab() === 'expenses'" (click)="setActiveTab('expenses')">Expenses</button>
            <button class="tab" [class.active]="activeTab() === 'approvals'" (click)="setActiveTab('approvals')">Approvals</button>
            <button class="tab" [class.active]="activeTab() === 'reports'" (click)="setActiveTab('reports')">Reports</button>
          </div>
          <button class="btn btn-primary">+ New Expense</button>
        </div>
        
        @if (activeTab() === 'expenses') {
          <app-expense-grid></app-expense-grid>
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
    .module-header { display: flex; justify-content: space-between; align-items: center; padding: 24px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; border-radius: 8px; margin-bottom: 24px; }
    .header-content h1 { margin: 0 0 4px 0; font-size: 1.75rem; }
    .subtitle { margin: 0; opacity: 0.8; }
    .ag-version { padding: 6px 12px; background: rgba(255,255,255,0.2); border-radius: 16px; font-size: 0.85rem; }
    .module-content { flex: 1; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .content-header { display: flex; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid #e5e7eb; }
    .tabs { display: flex; gap: 4px; }
    .tab { padding: 8px 16px; background: transparent; border: none; border-radius: 6px; font-weight: 500; color: #6b7280; cursor: pointer; }
    .tab:hover { background: #f3f4f6; }
    .tab.active { background: #f59e0b; color: white; }
    .btn { padding: 8px 16px; border: none; border-radius: 6px; font-weight: 500; cursor: pointer; }
    .btn-primary { background: #f59e0b; color: white; }
    .placeholder-content { padding: 48px; text-align: center; color: #6b7280; }
    
    .quick-nav { margin-top: 24px; padding: 24px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .quick-nav h3 { margin: 0 0 16px 0; font-size: 1rem; color: #374151; }
    .nav-cards { display: flex; gap: 12px; flex-wrap: wrap; }
    .nav-card { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
    .nav-card:hover { background: #e5e7eb; transform: translateY(-1px); }
    .nav-icon { font-size: 1.25rem; }
    .nav-name { font-weight: 500; color: #374151; }
    .nav-version { padding: 2px 6px; background: #fef3c7; color: #d97706; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EntryComponent implements OnInit {
  activeTab = signal<'expenses' | 'approvals' | 'reports'>('expenses');
  
  otherModules = [
    { path: '/reg-reporting', name: 'Regulatory', icon: '📋', agGrid: 'v31' },
    { path: '/financial-reporting', name: 'Financial', icon: '💰', agGrid: 'v30' },
    { path: '/tax-reporting', name: 'Tax', icon: '🧾', agGrid: 'v29' },
    { path: '/control-tower', name: 'Control Tower', icon: '🎯', agGrid: 'v31' }
  ];
  
  constructor(private router: Router) {}
  
  ngOnInit(): void { console.log('[ExpenseReporting] Module loaded - AG Grid v31.0.0'); }
  setActiveTab(tab: 'expenses' | 'approvals' | 'reports'): void { this.activeTab.set(tab); }
  
  navigateTo(path: string): void {
    this.router.navigate([path]);
  }
}
