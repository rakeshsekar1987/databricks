import React, { useState, useCallback, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ColDef, GridReadyEvent, GridApi } from 'ag-grid-community';

// Import AG Grid v29 styles
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
 * Uses AG Grid v29.x - demonstrating version isolation
 */
const TaxReportingGrid: React.FC = () => {
  const [gridApi, setGridApi] = useState<GridApi | null>(null);

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
  ]);

  const columnDefs = useMemo<ColDef<TaxReport>[]>(() => [
    {
      field: 'id',
      headerName: 'Report ID',
      width: 110,
      pinned: 'left',
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
      cellRenderer: (params: { value: string }) => {
        const statusColors: Record<string, string> = {
          Pending: '#ed8936',
          Filed: '#3182ce',
          Accepted: '#38a169',
          Amended: '#805ad5',
        };
        const color = statusColors[params.value] || '#718096';
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
            {params.value}
          </span>
        );
      },
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
      valueFormatter: (params) => {
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
        }).format(params.value);
      },
    },
    {
      field: 'preparer',
      headerName: 'Preparer',
      width: 120,
      filter: 'agTextColumnFilter',
    },
  ], []);

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    resizable: true,
    filter: true,
  }), []);

  const onGridReady = useCallback((params: GridReadyEvent) => {
    setGridApi(params.api);
  }, []);

  return (
    <div className="grid-container">
      <div className="grid-toolbar">
        <button
          className="toolbar-button"
          onClick={() => gridApi?.exportDataAsCsv()}
        >
          Export CSV
        </button>
        <button
          className="toolbar-button"
          onClick={() => gridApi?.setFilterModel(null)}
        >
          Clear Filters
        </button>
      </div>
      <div className="ag-theme-alpine" style={{ height: 400, width: '100%' }}>
        <AgGridReact
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          onGridReady={onGridReady}
          rowSelection="multiple"
          animateRows={true}
          pagination={true}
          paginationPageSize={10}
        />
      </div>
    </div>
  );
};

export default TaxReportingGrid;
