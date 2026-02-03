import { Component, OnInit, ChangeDetectionStrategy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
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
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EntryComponent implements OnInit {
  activeTab = signal<'expenses' | 'approvals' | 'reports'>('expenses');
  
  ngOnInit(): void { console.log('[ExpenseReporting] Module loaded - AG Grid v31.0.0'); }
  setActiveTab(tab: 'expenses' | 'approvals' | 'reports'): void { this.activeTab.set(tab); }
}
