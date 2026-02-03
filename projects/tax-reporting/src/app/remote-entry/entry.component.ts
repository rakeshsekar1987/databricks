import { Component, OnInit, ChangeDetectionStrategy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { TaxReportingGridComponent } from '../components/tax-reporting-grid/tax-reporting-grid.component';

/**
 * Tax Reporting Entry Component
 * 
 * Main entry point when loaded as a federated module.
 * Displays the Tax Reporting grid with AG Grid v29.
 */
@Component({
  selector: 'app-tax-entry',
  standalone: true,
  imports: [CommonModule, TaxReportingGridComponent],
  template: `
    <div class="module-container">
      <header class="module-header">
        <div class="header-content">
          <h1>Tax Reporting</h1>
          <p class="subtitle">Manage tax filings and compliance</p>
        </div>
        <div class="header-meta">
          <span class="ag-version">AG Grid v29.3.0</span>
          <span class="module-status" [class.online]="isOnline()">
            {{ isOnline() ? 'Online' : 'Offline' }}
          </span>
        </div>
      </header>
      
      <section class="module-content">
        <div class="content-header">
          <div class="tabs">
            <button 
              class="tab" 
              [class.active]="activeTab() === 'grid'"
              (click)="setActiveTab('grid')">
              Tax Reports
            </button>
            <button 
              class="tab" 
              [class.active]="activeTab() === 'summary'"
              (click)="setActiveTab('summary')">
              Summary
            </button>
            <button 
              class="tab" 
              [class.active]="activeTab() === 'filings'"
              (click)="setActiveTab('filings')">
              Filings
            </button>
          </div>
          
          <div class="actions">
            <button class="btn btn-primary">
              + New Tax Report
            </button>
          </div>
        </div>
        
        @if (activeTab() === 'grid') {
          <app-tax-reporting-grid></app-tax-reporting-grid>
        } @else if (activeTab() === 'summary') {
          <div class="placeholder-content">
            <h3>Tax Summary</h3>
            <p>Summary view coming soon...</p>
          </div>
        } @else {
          <div class="placeholder-content">
            <h3>Filed Reports</h3>
            <p>Filing history coming soon...</p>
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
      
      <footer class="module-footer">
        <span>Tax Reporting Module v1.0.0</span>
        <span>|</span>
        <span>AG Grid v29.3.0 (Legacy)</span>
      </footer>
    </div>
  `,
  styles: [`
    .module-container {
      display: flex;
      flex-direction: column;
      min-height: calc(100vh - 128px);
      background: #f8f9fa;
    }
    
    .module-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 24px;
      background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
      color: white;
      border-radius: 8px;
      margin-bottom: 24px;
    }
    
    .header-content h1 {
      margin: 0 0 4px 0;
      font-size: 1.75rem;
    }
    
    .subtitle {
      margin: 0;
      opacity: 0.8;
    }
    
    .header-meta {
      display: flex;
      gap: 12px;
    }
    
    .ag-version {
      padding: 6px 12px;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 16px;
      font-size: 0.85rem;
      font-weight: 500;
    }
    
    .module-status {
      padding: 6px 12px;
      background: rgba(239, 68, 68, 0.2);
      color: #fca5a5;
      border-radius: 16px;
      font-size: 0.85rem;
      font-weight: 500;
    }
    
    .module-status.online {
      background: rgba(34, 197, 94, 0.2);
      color: #86efac;
    }
    
    .module-content {
      flex: 1;
      background: white;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .content-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      border-bottom: 1px solid #e5e7eb;
    }
    
    .tabs {
      display: flex;
      gap: 4px;
    }
    
    .tab {
      padding: 8px 16px;
      background: transparent;
      border: none;
      border-radius: 6px;
      font-weight: 500;
      color: #6b7280;
      cursor: pointer;
      transition: all 0.2s;
    }
    
    .tab:hover {
      background: #f3f4f6;
    }
    
    .tab.active {
      background: #7c3aed;
      color: white;
    }
    
    .btn {
      padding: 8px 16px;
      border: none;
      border-radius: 6px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }
    
    .btn-primary {
      background: #7c3aed;
      color: white;
    }
    
    .btn-primary:hover {
      background: #6d28d9;
    }
    
    .placeholder-content {
      padding: 48px;
      text-align: center;
      color: #6b7280;
    }
    
    .placeholder-content h3 {
      margin-bottom: 8px;
      color: #374151;
    }
    
    .module-footer {
      display: flex;
      gap: 8px;
      justify-content: center;
      padding: 16px;
      color: #9ca3af;
      font-size: 0.85rem;
    }
    
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
      border-color: #d1d5db;
      transform: translateY(-1px);
    }
    
    .nav-icon {
      font-size: 1.25rem;
    }
    
    .nav-name {
      font-weight: 500;
      color: #374151;
    }
    
    .nav-version {
      padding: 2px 6px;
      background: #dbeafe;
      color: #1d4ed8;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EntryComponent implements OnInit {
  activeTab = signal<'grid' | 'summary' | 'filings'>('grid');
  isOnline = signal(true);
  
  // Other modules for cross-navigation
  otherModules = [
    { path: '/reg-reporting', name: 'Regulatory', icon: '📋', agGrid: 'v31' },
    { path: '/financial-reporting', name: 'Financial', icon: '💰', agGrid: 'v30' },
    { path: '/expense-reporting', name: 'Expense', icon: '💳', agGrid: 'v31' },
    { path: '/control-tower', name: 'Control Tower', icon: '🎯', agGrid: 'v31' }
  ];
  
  constructor(private router: Router) {}
  
  ngOnInit(): void {
    console.log('[TaxReporting] Module loaded - AG Grid v29.3.0');
  }
  
  setActiveTab(tab: 'grid' | 'summary' | 'filings'): void {
    this.activeTab.set(tab);
  }
  
  navigateTo(path: string): void {
    // Navigate using the shell's router
    this.router.navigate([path]);
  }
}
