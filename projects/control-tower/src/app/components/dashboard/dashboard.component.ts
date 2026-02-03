import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

interface ModuleStatus {
  name: string;
  version: string;
  status: 'online' | 'offline' | 'degraded';
  agGridVersion: string;
  lastHealthCheck: Date;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="dashboard-container">
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-value">5</div>
          <div class="stat-label">Total Modules</div>
        </div>
        <div class="stat-card success">
          <div class="stat-value">{{ onlineModules }}</div>
          <div class="stat-label">Online</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-value">{{ offlineModules }}</div>
          <div class="stat-label">Offline</div>
        </div>
        <div class="stat-card info">
          <div class="stat-value">3</div>
          <div class="stat-label">AG Grid Versions</div>
        </div>
      </div>
      
      <div class="modules-grid">
        <h3>Module Status</h3>
        <div class="module-cards">
          @for (module of modules; track module.name) {
            <div class="module-card" [class]="module.status">
              <div class="module-header">
                <span class="module-name">{{ module.name }}</span>
                <span class="status-badge" [class]="module.status">{{ module.status }}</span>
              </div>
              <div class="module-info">
                <div class="info-row">
                  <span class="label">Version:</span>
                  <span class="value">{{ module.version }}</span>
                </div>
                <div class="info-row">
                  <span class="label">AG Grid:</span>
                  <span class="value ag-badge">{{ module.agGridVersion }}</span>
                </div>
                <div class="info-row">
                  <span class="label">Last Check:</span>
                  <span class="value">{{ module.lastHealthCheck | date:'short' }}</span>
                </div>
              </div>
            </div>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    .dashboard-container { padding: 24px; }
    .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
    .stat-card { padding: 24px; background: #f8fafc; border-radius: 8px; text-align: center; border-left: 4px solid #e2e8f0; }
    .stat-card.success { border-left-color: #22c55e; }
    .stat-card.warning { border-left-color: #f59e0b; }
    .stat-card.info { border-left-color: #3b82f6; }
    .stat-value { font-size: 2.5rem; font-weight: 700; color: #1f2937; }
    .stat-label { font-size: 0.9rem; color: #6b7280; margin-top: 4px; }
    .modules-grid h3 { margin-bottom: 16px; color: #374151; }
    .module-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
    .module-card { padding: 20px; background: white; border: 1px solid #e5e7eb; border-radius: 8px; transition: box-shadow 0.2s; }
    .module-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .module-card.online { border-left: 4px solid #22c55e; }
    .module-card.offline { border-left: 4px solid #ef4444; }
    .module-card.degraded { border-left: 4px solid #f59e0b; }
    .module-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    .module-name { font-weight: 600; color: #1f2937; }
    .status-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
    .status-badge.online { background: #dcfce7; color: #166534; }
    .status-badge.offline { background: #fee2e2; color: #991b1b; }
    .status-badge.degraded { background: #fef3c7; color: #92400e; }
    .module-info { display: flex; flex-direction: column; gap: 8px; }
    .info-row { display: flex; justify-content: space-between; font-size: 0.9rem; }
    .label { color: #6b7280; }
    .value { color: #374151; font-weight: 500; }
    .ag-badge { padding: 2px 6px; background: #ede9fe; color: #7c3aed; border-radius: 4px; font-size: 0.8rem; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DashboardComponent implements OnInit {
  modules: ModuleStatus[] = [
    { name: 'Regulatory Reporting', version: '1.0.0', status: 'online', agGridVersion: 'v31', lastHealthCheck: new Date() },
    { name: 'Financial Reporting', version: '1.0.0', status: 'online', agGridVersion: 'v30', lastHealthCheck: new Date() },
    { name: 'Expense Reporting', version: '1.0.0', status: 'online', agGridVersion: 'v31', lastHealthCheck: new Date() },
    { name: 'Tax Reporting', version: '1.0.0', status: 'online', agGridVersion: 'v29', lastHealthCheck: new Date() },
    { name: 'Control Tower', version: '1.0.0', status: 'online', agGridVersion: 'v31', lastHealthCheck: new Date() }
  ];
  
  get onlineModules(): number { return this.modules.filter(m => m.status === 'online').length; }
  get offlineModules(): number { return this.modules.filter(m => m.status === 'offline').length; }
  
  ngOnInit(): void { console.log('[Dashboard] Initialized'); }
}
