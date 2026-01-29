#!/usr/bin/env python3
"""
Excel Reader Module for the Excel to JSON Transformation Framework.
Reads data from Excel files with multiple tabs and converts to dictionaries.
"""

import os
from typing import Dict, List, Any, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class ExcelReader:
    """
    Reads Excel files and extracts data from specified tabs.
    Supports both pandas and openpyxl for flexibility.
    """
    
    def __init__(self, file_path: str):
        """
        Initialize the Excel reader with a file path.
        
        Args:
            file_path: Path to the Excel file
        """
        self.file_path = file_path
        self._validate_file()
        
        if not PANDAS_AVAILABLE and not OPENPYXL_AVAILABLE:
            raise ImportError(
                "Neither pandas nor openpyxl is installed. "
                "Please install one of them: pip install pandas openpyxl"
            )
    
    def _validate_file(self):
        """Validate that the file exists."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Excel file not found: {self.file_path}")
    
    def get_sheet_names(self) -> List[str]:
        """Get list of sheet names in the Excel file."""
        if PANDAS_AVAILABLE:
            xl = pd.ExcelFile(self.file_path)
            return xl.sheet_names
        elif OPENPYXL_AVAILABLE:
            wb = openpyxl.load_workbook(self.file_path, read_only=True)
            return wb.sheetnames
    
    def read_sheet(self, sheet_name: str) -> List[Dict[str, Any]]:
        """
        Read a specific sheet and return as list of dictionaries.
        
        Args:
            sheet_name: Name of the sheet to read
            
        Returns:
            List of dictionaries, one per row
        """
        if PANDAS_AVAILABLE:
            return self._read_with_pandas(sheet_name)
        elif OPENPYXL_AVAILABLE:
            return self._read_with_openpyxl(sheet_name)
    
    def _read_with_pandas(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Read sheet using pandas."""
        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name)
            # Replace NaN with empty string for string columns, None for others
            df = df.fillna('')
            # Convert to list of dictionaries
            records = df.to_dict('records')
            return records
        except Exception as e:
            print(f"Warning: Could not read sheet '{sheet_name}': {e}")
            return []
    
    def _read_with_openpyxl(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Read sheet using openpyxl."""
        try:
            wb = openpyxl.load_workbook(self.file_path, read_only=True, data_only=True)
            ws = wb[sheet_name]
            
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return []
            
            # First row is header
            headers = [str(h) if h else f'Column_{i}' for i, h in enumerate(rows[0])]
            
            # Convert remaining rows to dictionaries
            records = []
            for row in rows[1:]:
                record = {}
                for i, value in enumerate(row):
                    if i < len(headers):
                        record[headers[i]] = value if value is not None else ''
                records.append(record)
            
            wb.close()
            return records
        except Exception as e:
            print(f"Warning: Could not read sheet '{sheet_name}': {e}")
            return []
    
    def read_all_sheets(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Read all sheets from the Excel file.
        
        Returns:
            Dictionary mapping sheet name to list of row dictionaries
        """
        result = {}
        for sheet_name in self.get_sheet_names():
            result[sheet_name] = self.read_sheet(sheet_name)
        return result
    
    def find_sheet_by_pattern(self, pattern: str) -> Optional[str]:
        """
        Find a sheet name that contains the given pattern (case-insensitive).
        
        Args:
            pattern: Pattern to search for in sheet names
            
        Returns:
            Matching sheet name or None
        """
        pattern_lower = pattern.lower()
        for sheet_name in self.get_sheet_names():
            if pattern_lower in sheet_name.lower():
                return sheet_name
        return None


def read_excel_data(file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Convenience function to read all data from an Excel file.
    
    Args:
        file_path: Path to the Excel file
        
    Returns:
        Dictionary mapping sheet name to list of row dictionaries
    """
    reader = ExcelReader(file_path)
    return reader.read_all_sheets()


if __name__ == "__main__":
    # Test the reader
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        reader = ExcelReader(file_path)
        print(f"Sheet names: {reader.get_sheet_names()}")
        for sheet in reader.get_sheet_names():
            data = reader.read_sheet(sheet)
            print(f"\n{sheet}: {len(data)} rows")
            if data:
                print(f"  Columns: {list(data[0].keys())}")
