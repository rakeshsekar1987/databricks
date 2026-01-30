import React, { useState, useMemo, useCallback } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ColDef, GridReadyEvent, GridApi } from 'ag-grid-community';

import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';

interface Expense {
  id: string;
  employee: string;
  department: string;
  category: string;
  amount: number;
  currency: string;
  date: string;
  status: 'Pending' | 'Approved' | 'Rejected' | 'Paid';
  description: string;
}

const ExpenseGrid: React.FC = () => {
  const [gridApi, setGridApi] = useState<GridApi | null>(null);

  const [rowData] = useState<Expense[]>([
    { id: 'EXP-001', employee: 'John Smith', department: 'Engineering', category: 'Travel', amount: 1250.00, currency: 'USD', date: '2024-01-15', status: 'Approved', description: 'Client visit - NYC' },
    { id: 'EXP-002', employee: 'Jane Doe', department: 'Marketing', category: 'Meals', amount: 85.50, currency: 'USD', date: '2024-01-16', status: 'Pending', description: 'Team lunch meeting' },
    { id: 'EXP-003', employee: 'Bob Wilson', department: 'Sales', category: 'Travel', amount: 2100.00, currency: 'USD', date: '2024-01-14', status: 'Paid', description: 'Conference travel' },
    { id: 'EXP-004', employee: 'Alice Brown', department: 'HR', category: 'Supplies', amount: 156.25, currency: 'USD', date: '2024-01-17', status: 'Rejected', description: 'Office supplies' },
    { id: 'EXP-005', employee: 'Charlie Davis', department: 'Finance', category: 'Software', amount: 299.99, currency: 'USD', date: '2024-01-18', status: 'Pending', description: 'Productivity tools' },
  ]);

  const columnDefs = useMemo<ColDef<Expense>[]>(() => [
    { field: 'id', headerName: 'Expense ID', width: 110, pinned: 'left' },
    { field: 'employee', headerName: 'Employee', width: 140 },
    { field: 'department', headerName: 'Department', width: 120 },
    { field: 'category', headerName: 'Category', width: 110 },
    { field: 'amount', headerName: 'Amount', width: 110, valueFormatter: p => `$${p.value.toFixed(2)}` },
    { field: 'date', headerName: 'Date', width: 110 },
    {
      field: 'status', headerName: 'Status', width: 110,
      cellRenderer: (params: { value: string }) => {
        const colors: Record<string, string> = { Pending: '#ed8936', Approved: '#38a169', Rejected: '#e53e3e', Paid: '#3182ce' };
        return <span style={{ color: colors[params.value], fontWeight: 500, padding: '2px 8px', borderRadius: '4px', backgroundColor: `${colors[params.value]}20` }}>{params.value}</span>;
      },
    },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 200 },
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

export default ExpenseGrid;
