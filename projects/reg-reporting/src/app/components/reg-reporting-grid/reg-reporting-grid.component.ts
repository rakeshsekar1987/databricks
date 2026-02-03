import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AgGridModule } from 'ag-grid-angular';
import { ColDef, GridReadyEvent, GridApi } from 'ag-grid-community';

// Note: AG Grid styles are included via angular.json

interface RegReport {
  id: string;
  reportName: string;
  regulator: string;
  jurisdiction: string;
  frequency: string;
  dueDate: string;
  status: string;
  submittedDate: string | null;
}

@Component({
  selector: 'app-reg-reporting-grid',
  standalone: true,
  imports: [CommonModule, AgGridModule],
  template: `
    <div class="grid-container">
      <div class="grid-toolbar">
        <div class="toolbar-left">
          <button class="toolbar-btn" (click)="onRefresh()">🔄 Refresh</button>
          <button class="toolbar-btn" (click)="onExport()">📥 Export</button>
        </div>
        <div class="toolbar-right">
          <span class="record-count">{{ rowData.length }} reports</span>
          <span class="version-info">AG Grid v31</span>
        </div>
      </div>
      <div class="ag-theme-alpine grid-wrapper">
        <ag-grid-angular style="width: 100%; height: 500px;" [rowData]="rowData" [columnDefs]="columnDefs" [defaultColDef]="defaultColDef" [animateRows]="true" [pagination]="true" [paginationPageSize]="10" (gridReady)="onGridReady($event)"></ag-grid-angular>
      </div>
    </div>
  `,
  styles: [`
    .grid-container { padding: 16px 24px 24px; }
    .grid-toolbar { display: flex; justify-content: space-between; margin-bottom: 16px; }
    .toolbar-left { display: flex; gap: 8px; }
    .toolbar-btn { padding: 8px 12px; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 6px; cursor: pointer; }
    .toolbar-right { display: flex; align-items: center; gap: 16px; }
    .record-count { color: #6b7280; font-size: 0.9rem; }
    .version-info { padding: 4px 8px; background: #dbeafe; color: #2563eb; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
    .grid-wrapper { border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RegReportingGridComponent implements OnInit {
  private gridApi!: GridApi;
  
  rowData: RegReport[] = [
    { id: 'REG-001', reportName: 'Basel III Capital', regulator: 'Federal Reserve', jurisdiction: 'US', frequency: 'Quarterly', dueDate: '2024-03-31', status: 'Submitted', submittedDate: '2024-03-28' },
    { id: 'REG-002', reportName: 'CCAR Stress Test', regulator: 'Federal Reserve', jurisdiction: 'US', frequency: 'Annual', dueDate: '2024-04-05', status: 'In Progress', submittedDate: null },
    { id: 'REG-003', reportName: 'MiFID II', regulator: 'ESMA', jurisdiction: 'EU', frequency: 'Daily', dueDate: '2024-03-15', status: 'Submitted', submittedDate: '2024-03-15' },
    { id: 'REG-004', reportName: 'Dodd-Frank', regulator: 'SEC', jurisdiction: 'US', frequency: 'Monthly', dueDate: '2024-03-31', status: 'Pending', submittedDate: null },
    { id: 'REG-005', reportName: 'GDPR Compliance', regulator: 'ICO', jurisdiction: 'UK', frequency: 'Annual', dueDate: '2024-05-25', status: 'Not Started', submittedDate: null }
  ];
  
  columnDefs: ColDef<RegReport>[] = [
    { field: 'id', headerName: 'Report ID', width: 100, pinned: 'left' },
    { field: 'reportName', headerName: 'Report Name', flex: 1, minWidth: 180 },
    { field: 'regulator', headerName: 'Regulator', width: 130 },
    { field: 'jurisdiction', headerName: 'Jurisdiction', width: 100 },
    { field: 'frequency', headerName: 'Frequency', width: 100 },
    { field: 'dueDate', headerName: 'Due Date', width: 120 },
    { field: 'status', headerName: 'Status', width: 120 },
    { field: 'submittedDate', headerName: 'Submitted', width: 120 }
  ];
  
  defaultColDef: ColDef = { sortable: true, resizable: true, filter: true };
  
  ngOnInit(): void { console.log('[RegReportingGrid] Initialized with AG Grid v31'); }
  onGridReady(params: GridReadyEvent): void { this.gridApi = params.api; }
  onRefresh(): void { this.gridApi?.refreshCells(); }
  onExport(): void { this.gridApi?.exportDataAsCsv({ fileName: `reg-reports-${new Date().toISOString().split('T')[0]}.csv` }); }
}
