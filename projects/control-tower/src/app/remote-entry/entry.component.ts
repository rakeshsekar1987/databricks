import { Component, OnInit, ChangeDetectionStrategy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
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
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EntryComponent implements OnInit {
  activeTab = signal<'dashboard' | 'modules' | 'health'>('dashboard');
  
  ngOnInit(): void { console.log('[ControlTower] Module loaded - AG Grid v31.0.0'); }
  setActiveTab(tab: 'dashboard' | 'modules' | 'health'): void { this.activeTab.set(tab); }
}
