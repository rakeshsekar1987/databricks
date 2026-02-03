import { Component, OnInit, ChangeDetectionStrategy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AgGridModule } from 'ag-grid-angular';
import { ColDef, GridReadyEvent, GridApi, ValueFormatterParams } from 'ag-grid-community';

import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

interface FinancialStatement {
  id: string;
  period: string;
  type: string;
  entity: string;
  revenue: number;
  expenses: number;
  netIncome: number;
  status: string;
}

@Component({
  selector: 'app-financial-grid',
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
          <span class="record-count">{{ rowData.length }} statements</span>
          <span class="version-info">AG Grid v30</span>
        </div>
      </div>
      
      <div class="ag-theme-alpine grid-wrapper">
        <ag-grid-angular
          style="width: 100%; height: 500px;"
          [rowData]="rowData"
          [columnDefs]="columnDefs"
          [defaultColDef]="defaultColDef"
          [animateRows]="true"
          [pagination]="true"
          [paginationPageSize]="10"
          (gridReady)="onGridReady($event)">
        </ag-grid-angular>
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
    .version-info { padding: 4px 8px; background: #d1fae5; color: #059669; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
    .grid-wrapper { border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FinancialGridComponent implements OnInit {
  private gridApi!: GridApi;
  
  rowData: FinancialStatement[] = [
    { id: 'FIN-001', period: 'Q4 2023', type: 'Income Statement', entity: 'Acme Corp', revenue: 5200000, expenses: 3800000, netIncome: 1400000, status: 'Approved' },
    { id: 'FIN-002', period: 'Q4 2023', type: 'Balance Sheet', entity: 'Acme Corp', revenue: 0, expenses: 0, netIncome: 0, status: 'Approved' },
    { id: 'FIN-003', period: 'Q4 2023', type: 'Cash Flow', entity: 'Acme Corp', revenue: 5200000, expenses: 4100000, netIncome: 1100000, status: 'Pending' },
    { id: 'FIN-004', period: 'Q3 2023', type: 'Income Statement', entity: 'Acme Corp', revenue: 4800000, expenses: 3500000, netIncome: 1300000, status: 'Approved' },
    { id: 'FIN-005', period: 'Q4 2023', type: 'Income Statement', entity: 'Acme EU', revenue: 2100000, expenses: 1600000, netIncome: 500000, status: 'Draft' }
  ];
  
  columnDefs: ColDef<FinancialStatement>[] = [
    { field: 'id', headerName: 'Statement ID', width: 120, pinned: 'left' },
    { field: 'period', headerName: 'Period', width: 100 },
    { field: 'type', headerName: 'Type', flex: 1, minWidth: 150 },
    { field: 'entity', headerName: 'Entity', width: 130 },
    { field: 'revenue', headerName: 'Revenue', width: 130, valueFormatter: (p: ValueFormatterParams) => this.formatCurrency(p.value), cellStyle: { textAlign: 'right' } },
    { field: 'expenses', headerName: 'Expenses', width: 130, valueFormatter: (p: ValueFormatterParams) => this.formatCurrency(p.value), cellStyle: { textAlign: 'right' } },
    { field: 'netIncome', headerName: 'Net Income', width: 130, valueFormatter: (p: ValueFormatterParams) => this.formatCurrency(p.value), cellStyle: { textAlign: 'right' } },
    { field: 'status', headerName: 'Status', width: 100 }
  ];
  
  defaultColDef: ColDef = { sortable: true, resizable: true, filter: true };
  
  ngOnInit(): void {
    console.log('[FinancialGrid] Initialized with AG Grid v30');
  }
  
  onGridReady(params: GridReadyEvent): void { this.gridApi = params.api; }
  onRefresh(): void { this.gridApi?.refreshCells(); }
  onExport(): void { this.gridApi?.exportDataAsCsv({ fileName: `financial-${new Date().toISOString().split('T')[0]}.csv` }); }
  
  private formatCurrency(value: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(value);
  }
}
