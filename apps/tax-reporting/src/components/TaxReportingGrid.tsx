import React, { useState, useCallback, useMemo, useRef } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, GridReadyEvent, GridApi, FilterChangedEvent } from 'ag-grid-community';

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
 * Uses AG Grid v29.x
 */
const TaxReportingGrid: React.FC = () => {
  const gridRef = useRef<AgGridReact>(null);
  const [gridApi, setGridApi] = useState<GridApi | null>(null);
  const [filterCount, setFilterCount] = useState(0);

  // Sample data
  const [rowData] = useState<TaxReport[]>([
    {
      id: 'TAX-001',
      taxYear: 2023,
      reportType: 'Corporate Income Tax',
      entityName: 'Acme Corp',
      jurisdiction: 'Federal',
      status: 'Filed',
      filingDeadline: '2024-04-15',
      taxLiability: 1250000,
      preparer: 'Tax Team A',
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
      preparer: 'Tax Team A',
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
      preparer: 'Tax Team B',
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
      preparer: 'Tax Team C',
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
      preparer: 'Tax Team B',
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
      preparer: 'Tax Team A',
    },
  ]);

  // Column definitions
  const columnDefs = useMemo<ColDef<TaxReport>[]>(() => [
    {
      field: 'id',
      headerName: 'Report ID',
      width: 110,
      pinned: 'left',
      filter: 'agTextColumnFilter',
    },
    {
      field: 'taxYear',
      headerName: 'Tax Year',
      width: 100,
      filter: 'agNumberColumnFilter',
    },
    {
      field: 'reportType',
      headerName: 'Report Type',
      flex: 1,
      minWidth: 180,
      filter: 'agTextColumnFilter',
    },
    {
      field: 'entityName',
      headerName: 'Entity',
      width: 150,
      filter: 'agTextColumnFilter',
    },
    {
      field: 'jurisdiction',
      headerName: 'Jurisdiction',
      width: 130,
      filter: 'agSetColumnFilter',
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      filter: 'agSetColumnFilter',
      cellRenderer: StatusCellRenderer,
    },
    {
      field: 'filingDeadline',
      headerName: 'Filing Deadline',
      width: 140,
      filter: 'agDateColumnFilter',
    },
    {
      field: 'taxLiability',
      headerName: 'Tax Liability',
      width: 140,
      filter: 'agNumberColumnFilter',
      valueFormatter: (params) => formatCurrency(params.value),
      cellStyle: { textAlign: 'right' },
    },
    {
      field: 'preparer',
      headerName: 'Preparer',
      width: 120,
      filter: 'agTextColumnFilter',
    },
  ], []);

  // Default column definition
  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    resizable: true,
    filter: true,
  }), []);

  // Grid event handlers
  const onGridReady = useCallback((params: GridReadyEvent) => {
    setGridApi(params.api);
  }, []);

  const onFilterChanged = useCallback((event: FilterChangedEvent) => {
    const filterModel = event.api.getFilterModel();
    setFilterCount(Object.keys(filterModel).length);
  }, []);

  // Action handlers
  const handleExport = useCallback(() => {
    gridApi?.exportDataAsCsv({
      fileName: `tax-reports-${new Date().toISOString().split('T')[0]}.csv`,
    });
  }, [gridApi]);

  const handleClearFilters = useCallback(() => {
    gridApi?.setFilterModel(null);
  }, [gridApi]);

  const handleRefresh = useCallback(() => {
    // In production, this would fetch fresh data
    gridRef.current?.api?.refreshCells();
  }, []);

  return (
    <div className="grid-container">
      <div className="grid-toolbar">
        <div className="toolbar-left">
          <button className="toolbar-button" onClick={handleRefresh} title="Refresh">
            🔄 Refresh
          </button>
          <button className="toolbar-button" onClick={handleExport} title="Export to CSV">
            📥 Export CSV
          </button>
          {filterCount > 0 && (
            <button 
              className="toolbar-button toolbar-button-secondary" 
              onClick={handleClearFilters}
            >
              ✕ Clear Filters ({filterCount})
            </button>
          )}
        </div>
        <div className="toolbar-right">
          <span className="row-count">
            {rowData.length} records
          </span>
        </div>
      </div>
      
      <div className="ag-theme-alpine grid-wrapper">
        <AgGridReact
          ref={gridRef}
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          onGridReady={onGridReady}
          onFilterChanged={onFilterChanged}
          rowSelection="multiple"
          animateRows={true}
          pagination={true}
          paginationPageSize={10}
          paginationPageSizeSelector={[10, 25, 50]}
          suppressRowClickSelection={true}
          enableCellTextSelection={true}
        />
      </div>
    </div>
  );
};

// Status cell renderer
const StatusCellRenderer: React.FC<{ value: string }> = ({ value }) => {
  const statusColors: Record<string, string> = {
    Pending: '#ed8936',
    Filed: '#3182ce',
    Accepted: '#38a169',
    Amended: '#805ad5',
  };
  
  const color = statusColors[value] || '#718096';
  
  return (
    <span
      style={{
        color,
        fontWeight: 500,
        padding: '2px 8px',
        borderRadius: '4px',
        backgroundColor: `${color}20`,
      }}
    >
      {value}
    </span>
  );
};

// Currency formatter
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export default TaxReportingGrid;
