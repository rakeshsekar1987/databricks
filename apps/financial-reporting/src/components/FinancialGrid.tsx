import React, { useState, useCallback, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ColDef, GridReadyEvent, GridApi } from 'ag-grid-community';

import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

interface FinancialReport {
  id: string;
  reportName: string;
  period: string;
  type: string;
  status: 'Draft' | 'Review' | 'Approved' | 'Published';
  revenue: number;
  expenses: number;
  netIncome: number;
  preparedBy: string;
}

/**
 * Financial Grid Component
 * Uses AG Grid v30.x
 */
const FinancialGrid: React.FC = () => {
  const [gridApi, setGridApi] = useState<GridApi | null>(null);

  const [rowData] = useState<FinancialReport[]>([
    { id: 'FIN-001', reportName: 'Q4 2023 Income Statement', period: 'Q4 2023', type: 'Income Statement', status: 'Published', revenue: 5200000, expenses: 3800000, netIncome: 1400000, preparedBy: 'Finance Team' },
    { id: 'FIN-002', reportName: 'Annual Balance Sheet 2023', period: 'FY 2023', type: 'Balance Sheet', status: 'Approved', revenue: 21000000, expenses: 15500000, netIncome: 5500000, preparedBy: 'Finance Team' },
    { id: 'FIN-003', reportName: 'Q1 2024 Cash Flow', period: 'Q1 2024', type: 'Cash Flow', status: 'Review', revenue: 4800000, expenses: 3600000, netIncome: 1200000, preparedBy: 'Treasury' },
    { id: 'FIN-004', reportName: 'Monthly P&L January', period: 'Jan 2024', type: 'P&L', status: 'Draft', revenue: 1650000, expenses: 1200000, netIncome: 450000, preparedBy: 'Accounting' },
  ]);

  const columnDefs = useMemo<ColDef<FinancialReport>[]>(() => [
    { field: 'id', headerName: 'Report ID', width: 110, pinned: 'left' },
    { field: 'reportName', headerName: 'Report Name', flex: 1, minWidth: 200 },
    { field: 'period', headerName: 'Period', width: 100 },
    { field: 'type', headerName: 'Type', width: 140 },
    {
      field: 'status', headerName: 'Status', width: 110,
      cellRenderer: (params: { value: string }) => {
        const colors: Record<string, string> = { Draft: '#718096', Review: '#ed8936', Approved: '#38a169', Published: '#3182ce' };
        return <span style={{ color: colors[params.value] || '#718096', fontWeight: 500, padding: '2px 8px', borderRadius: '4px', backgroundColor: `${colors[params.value]}20` }}>{params.value}</span>;
      },
    },
    { field: 'revenue', headerName: 'Revenue', width: 130, valueFormatter: p => `$${(p.value / 1000000).toFixed(2)}M` },
    { field: 'expenses', headerName: 'Expenses', width: 130, valueFormatter: p => `$${(p.value / 1000000).toFixed(2)}M` },
    { field: 'netIncome', headerName: 'Net Income', width: 130, valueFormatter: p => `$${(p.value / 1000000).toFixed(2)}M` },
    { field: 'preparedBy', headerName: 'Prepared By', width: 120 },
  ], []);

  const defaultColDef = useMemo<ColDef>(() => ({ sortable: true, resizable: true, filter: true }), []);
  const onGridReady = useCallback((params: GridReadyEvent) => setGridApi(params.api), []);

  return (
    <div className="grid-container">
      <div className="grid-toolbar">
        <button className="toolbar-button" onClick={() => gridApi?.exportDataAsCsv()}>Export CSV</button>
        <button className="toolbar-button" onClick={() => gridApi?.setFilterModel(null)}>Clear Filters</button>
      </div>
      <div className="ag-theme-alpine" style={{ height: 400, width: '100%' }}>
        <AgGridReact rowData={rowData} columnDefs={columnDefs} defaultColDef={defaultColDef} onGridReady={onGridReady} rowSelection="multiple" animateRows pagination paginationPageSize={10} />
      </div>
    </div>
  );
};

export default FinancialGrid;
