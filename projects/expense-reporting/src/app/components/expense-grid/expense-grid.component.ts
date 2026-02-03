import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AgGridModule } from 'ag-grid-angular';
import { ColDef, GridReadyEvent, GridApi, ValueFormatterParams } from 'ag-grid-community';

// Note: AG Grid styles are included via angular.json

interface Expense {
  id: string;
  date: string;
  category: string;
  description: string;
  vendor: string;
  amount: number;
  currency: string;
  status: string;
  submittedBy: string;
}

@Component({
  selector: 'app-expense-grid',
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
          <span class="record-count">{{ rowData.length }} expenses</span>
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
    .version-info { padding: 4px 8px; background: #fef3c7; color: #d97706; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
    .grid-wrapper { border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ExpenseGridComponent implements OnInit {
  private gridApi!: GridApi;
  
  rowData: Expense[] = [
    { id: 'EXP-001', date: '2024-03-01', category: 'Travel', description: 'Flight to NYC', vendor: 'United Airlines', amount: 450, currency: 'USD', status: 'Approved', submittedBy: 'John Doe' },
    { id: 'EXP-002', date: '2024-03-02', category: 'Meals', description: 'Client dinner', vendor: 'Nobu Restaurant', amount: 285, currency: 'USD', status: 'Pending', submittedBy: 'Jane Smith' },
    { id: 'EXP-003', date: '2024-03-05', category: 'Lodging', description: 'Hotel NYC 3 nights', vendor: 'Marriott', amount: 890, currency: 'USD', status: 'Approved', submittedBy: 'John Doe' },
    { id: 'EXP-004', date: '2024-03-07', category: 'Transport', description: 'Uber rides', vendor: 'Uber', amount: 125, currency: 'USD', status: 'Approved', submittedBy: 'John Doe' },
    { id: 'EXP-005', date: '2024-03-10', category: 'Equipment', description: 'Monitor', vendor: 'Amazon', amount: 350, currency: 'USD', status: 'Rejected', submittedBy: 'Mike Johnson' }
  ];
  
  columnDefs: ColDef<Expense>[] = [
    { field: 'id', headerName: 'Expense ID', width: 110, pinned: 'left' },
    { field: 'date', headerName: 'Date', width: 110 },
    { field: 'category', headerName: 'Category', width: 100 },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 180 },
    { field: 'vendor', headerName: 'Vendor', width: 140 },
    { field: 'amount', headerName: 'Amount', width: 110, valueFormatter: (p: ValueFormatterParams) => `$${p.value?.toFixed(2)}`, cellStyle: { textAlign: 'right' } },
    { field: 'status', headerName: 'Status', width: 100 },
    { field: 'submittedBy', headerName: 'Submitted By', width: 130 }
  ];
  
  defaultColDef: ColDef = { sortable: true, resizable: true, filter: true };
  
  ngOnInit(): void { console.log('[ExpenseGrid] Initialized with AG Grid v31'); }
  onGridReady(params: GridReadyEvent): void { this.gridApi = params.api; }
  onRefresh(): void { this.gridApi?.refreshCells(); }
  onExport(): void { this.gridApi?.exportDataAsCsv({ fileName: `expenses-${new Date().toISOString().split('T')[0]}.csv` }); }
}
