import { Component, OnInit, ChangeDetectionStrategy, signal, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AgGridModule } from 'ag-grid-angular';
import { 
  ColDef, 
  GridReadyEvent, 
  GridApi,
  ValueFormatterParams,
  ICellRendererParams 
} from 'ag-grid-community';

// AG Grid v29 styles
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

interface TaxReport {
  id: string;
  taxYear: number;
  reportType: string;
  entityName: string;
  jurisdiction: string;
  status: 'Pending' | 'Filed' | 'Accepted' | 'Amended';
  filingDeadline: string;
  taxLiability: number;
  preparer: string;
}

/**
 * Tax Reporting Grid Component
 * 
 * Displays tax reports using AG Grid v29.3.0.
 * Demonstrates version isolation in Module Federation.
 */
@Component({
  selector: 'app-tax-reporting-grid',
  standalone: true,
  imports: [CommonModule, AgGridModule],
  template: `
    <div class="grid-container">
      <div class="grid-toolbar">
        <div class="toolbar-left">
          <button class="toolbar-btn" (click)="onRefresh()" title="Refresh">
            🔄 Refresh
          </button>
          <button class="toolbar-btn" (click)="onExport()" title="Export">
            📥 Export CSV
          </button>
          @if (filterCount() > 0) {
            <button class="toolbar-btn secondary" (click)="onClearFilters()">
              ✕ Clear Filters ({{ filterCount() }})
            </button>
          }
        </div>
        <div class="toolbar-right">
          <span class="record-count">{{ rowData.length }} records</span>
          <span class="version-info">AG Grid v29</span>
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
          [rowSelection]="'multiple'"
          [suppressRowClickSelection]="true"
          (gridReady)="onGridReady($event)"
          (filterChanged)="onFilterChanged()">
        </ag-grid-angular>
      </div>
    </div>
  `,
  styles: [`
    .grid-container {
      padding: 16px 24px 24px;
    }
    
    .grid-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    
    .toolbar-left {
      display: flex;
      gap: 8px;
    }
    
    .toolbar-btn {
      padding: 8px 12px;
      background: #f3f4f6;
      border: 1px solid #e5e7eb;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.9rem;
      transition: all 0.2s;
    }
    
    .toolbar-btn:hover {
      background: #e5e7eb;
    }
    
    .toolbar-btn.secondary {
      background: #fef3c7;
      border-color: #fcd34d;
      color: #92400e;
    }
    
    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    
    .record-count {
      color: #6b7280;
      font-size: 0.9rem;
    }
    
    .version-info {
      padding: 4px 8px;
      background: #f3e8ff;
      color: #7c3aed;
      border-radius: 4px;
      font-size: 0.8rem;
      font-weight: 600;
    }
    
    .grid-wrapper {
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    :host ::ng-deep .ag-header {
      background: #f9fafb;
    }
    
    :host ::ng-deep .ag-row:hover {
      background: #f3f4f6 !important;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TaxReportingGridComponent implements OnInit {
  private gridApi!: GridApi;
  filterCount = signal(0);
  
  // Sample data
  rowData: TaxReport[] = [
    {
      id: 'TAX-001',
      taxYear: 2023,
      reportType: 'Corporate Income Tax',
      entityName: 'Acme Corp',
      jurisdiction: 'Federal',
      status: 'Filed',
      filingDeadline: '2024-04-15',
      taxLiability: 1250000,
      preparer: 'Tax Team A'
    },
    {
      id: 'TAX-002',
      taxYear: 2023,
      reportType: 'State Income Tax',
      entityName: 'Acme Corp',
      jurisdiction: 'California',
      status: 'Pending',
      filingDeadline: '2024-04-15',
      taxLiability: 425000,
      preparer: 'Tax Team A'
    },
    {
      id: 'TAX-003',
      taxYear: 2023,
      reportType: 'VAT Return',
      entityName: 'Acme EU Ltd',
      jurisdiction: 'Germany',
      status: 'Accepted',
      filingDeadline: '2024-01-31',
      taxLiability: 180000,
      preparer: 'Tax Team B'
    },
    {
      id: 'TAX-004',
      taxYear: 2023,
      reportType: 'Transfer Pricing',
      entityName: 'Acme Global',
      jurisdiction: 'OECD',
      status: 'Amended',
      filingDeadline: '2024-06-30',
      taxLiability: 0,
      preparer: 'Tax Team C'
    },
    {
      id: 'TAX-005',
      taxYear: 2023,
      reportType: 'Withholding Tax',
      entityName: 'Acme UK Ltd',
      jurisdiction: 'United Kingdom',
      status: 'Filed',
      filingDeadline: '2024-03-31',
      taxLiability: 95000,
      preparer: 'Tax Team B'
    },
    {
      id: 'TAX-006',
      taxYear: 2024,
      reportType: 'Quarterly Estimated Tax',
      entityName: 'Acme Corp',
      jurisdiction: 'Federal',
      status: 'Pending',
      filingDeadline: '2024-04-15',
      taxLiability: 320000,
      preparer: 'Tax Team A'
    }
  ];
  
  // Column definitions
  columnDefs: ColDef<TaxReport>[] = [
    {
      field: 'id',
      headerName: 'Report ID',
      width: 110,
      pinned: 'left',
      filter: 'agTextColumnFilter',
      checkboxSelection: true
    },
    {
      field: 'taxYear',
      headerName: 'Tax Year',
      width: 100,
      filter: 'agNumberColumnFilter'
    },
    {
      field: 'reportType',
      headerName: 'Report Type',
      flex: 1,
      minWidth: 180,
      filter: 'agTextColumnFilter'
    },
    {
      field: 'entityName',
      headerName: 'Entity',
      width: 150,
      filter: 'agTextColumnFilter'
    },
    {
      field: 'jurisdiction',
      headerName: 'Jurisdiction',
      width: 130,
      filter: 'agSetColumnFilter'
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      filter: 'agSetColumnFilter',
      cellRenderer: this.statusCellRenderer
    },
    {
      field: 'filingDeadline',
      headerName: 'Filing Deadline',
      width: 140,
      filter: 'agDateColumnFilter'
    },
    {
      field: 'taxLiability',
      headerName: 'Tax Liability',
      width: 140,
      filter: 'agNumberColumnFilter',
      valueFormatter: (params: ValueFormatterParams) => this.formatCurrency(params.value),
      cellStyle: { textAlign: 'right' }
    },
    {
      field: 'preparer',
      headerName: 'Preparer',
      width: 120,
      filter: 'agTextColumnFilter'
    }
  ];
  
  // Default column definition
  defaultColDef: ColDef = {
    sortable: true,
    resizable: true,
    filter: true
  };
  
  ngOnInit(): void {
    console.log('[TaxReportingGrid] Initialized with AG Grid v29');
  }
  
  onGridReady(params: GridReadyEvent): void {
    this.gridApi = params.api;
  }
  
  onFilterChanged(): void {
    const filterModel = this.gridApi?.getFilterModel();
    this.filterCount.set(filterModel ? Object.keys(filterModel).length : 0);
  }
  
  onRefresh(): void {
    this.gridApi?.refreshCells();
    console.log('[TaxReportingGrid] Grid refreshed');
  }
  
  onExport(): void {
    this.gridApi?.exportDataAsCsv({
      fileName: `tax-reports-${new Date().toISOString().split('T')[0]}.csv`
    });
  }
  
  onClearFilters(): void {
    this.gridApi?.setFilterModel(null);
    this.filterCount.set(0);
  }
  
  private statusCellRenderer(params: ICellRendererParams): string {
    const statusColors: Record<string, string> = {
      Pending: '#ed8936',
      Filed: '#3182ce',
      Accepted: '#38a169',
      Amended: '#805ad5'
    };
    
    const color = statusColors[params.value] || '#718096';
    
    return `<span style="
      color: ${color};
      font-weight: 500;
      padding: 2px 8px;
      border-radius: 4px;
      background-color: ${color}20;
    ">${params.value}</span>`;
  }
  
  private formatCurrency(value: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  }
}
