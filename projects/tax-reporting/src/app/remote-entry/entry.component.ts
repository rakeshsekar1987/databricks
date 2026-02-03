import { Component, OnInit, ChangeDetectionStrategy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
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
  imports: [CommonModule, RouterLink, TaxReportingGridComponent],
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
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EntryComponent implements OnInit {
  activeTab = signal<'grid' | 'summary' | 'filings'>('grid');
  isOnline = signal(true);
  
  ngOnInit(): void {
    console.log('[TaxReporting] Module loaded - AG Grid v29.3.0');
  }
  
  setActiveTab(tab: 'grid' | 'summary' | 'filings'): void {
    this.activeTab.set(tab);
  }
}
