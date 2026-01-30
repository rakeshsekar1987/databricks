import React, { useState, useCallback, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ColDef, GridReadyEvent, GridApi } from 'ag-grid-community';

// Import AG Grid styles
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

interface RegReport {
  id: string;
  reportName: string;
  reportType: string;
  status: 'Draft' | 'Submitted' | 'Approved' | 'Rejected';
  submissionDate: string;
  regulator: string;
  jurisdiction: string;
  assignee: string;
}

/**
 * Regulatory Reporting Grid Component
 * Uses AG Grid v31.x with Enterprise features
 */
const RegReportingGrid: React.FC = () => {
  const [gridApi, setGridApi] = useState<GridApi | null>(null);
  
  // Sample data for regulatory reports
  const [rowData] = useState<RegReport[]>([
    {
      id: 'REG-001',
      reportName: 'CCAR Stress Test Report',
      reportType: 'CCAR',
      status: 'Submitted',
      submissionDate: '2024-01-15',
      regulator: 'Federal Reserve',
      jurisdiction: 'US',
      assignee: 'John Smith',
    },
    {
      id: 'REG-002',
      reportName: 'Basel III Liquidity Report',
      reportType: 'Basel III',
      status: 'Draft',
      submissionDate: '2024-01-20',
      regulator: 'BIS',
      jurisdiction: 'Global',
      assignee: 'Jane Doe',
    },
    {
      id: 'REG-003',
      reportName: 'MiFID II Transaction Report',
      reportType: 'MiFID II',
      status: 'Approved',
      submissionDate: '2024-01-10',
      regulator: 'ESMA',
      jurisdiction: 'EU',
      assignee: 'Bob Wilson',
    },
    {
      id: 'REG-004',
      reportName: 'Dodd-Frank Swap Report',
      reportType: 'Dodd-Frank',
      status: 'Submitted',
      submissionDate: '2024-01-18',
      regulator: 'CFTC',
      jurisdiction: 'US',
      assignee: 'Alice Brown',
    },
    {
      id: 'REG-005',
      reportName: 'GDPR Compliance Report',
      reportType: 'GDPR',
      status: 'Rejected',
      submissionDate: '2024-01-12',
      regulator: 'ICO',
      jurisdiction: 'UK',
      assignee: 'Charlie Davis',
    },
  ]);

  // Column definitions with AG Grid v31 features
  const columnDefs = useMemo<ColDef<RegReport>[]>(() => [
    {
      field: 'id',
      headerName: 'Report ID',
      width: 120,
      pinned: 'left',
    },
    {
      field: 'reportName',
      headerName: 'Report Name',
      flex: 1,
      minWidth: 200,
      filter: 'agTextColumnFilter',
    },
    {
      field: 'reportType',
      headerName: 'Type',
      width: 120,
      filter: 'agSetColumnFilter',
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      cellRenderer: (params: { value: string }) => {
        const statusColors: Record<string, string> = {
          Draft: '#718096',
          Submitted: '#3182ce',
          Approved: '#38a169',
          Rejected: '#e53e3e',
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
      field: 'submissionDate',
      headerName: 'Submission Date',
      width: 150,
      filter: 'agDateColumnFilter',
    },
    {
      field: 'regulator',
      headerName: 'Regulator',
      width: 140,
      filter: 'agSetColumnFilter',
    },
    {
      field: 'jurisdiction',
      headerName: 'Jurisdiction',
      width: 120,
      filter: 'agSetColumnFilter',
    },
    {
      field: 'assignee',
      headerName: 'Assignee',
      width: 130,
      filter: 'agTextColumnFilter',
    },
  ], []);

  // Default column definition
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

export default RegReportingGrid;
