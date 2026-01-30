#!/usr/bin/env python3
"""
Main Execution Script for Excel to JSON Transformation Framework.

This script reads data from an Excel file with multiple tabs and generates
5 JSON output files.

Usage:
    python run_transformation.py --input <excel_file> --output <output_folder>
    
Example:
    python run_transformation.py --input "C:\\Users\\Demo\\Input\\data.xlsx" --output "C:\\Users\\Demo\\Output"
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime

from excel_reader import ExcelReader
from excel_to_json_transformer import (
    ExcelToJSONTransformer,
    KRIMaster,
    get_output_file_names
)


# =============================================================================
# Configuration - Sheet Name Mappings
# =============================================================================

# These are the expected sheet names (or patterns to match)
SHEET_CONFIG = {
    'cards': ['Cards', 'Card'],
    'funds': ['Funds', 'Fund'],
    'validations_trimmed': ['Validations - TRIMMED', 'TRIMMED', 'Trimmed', 'Normal Validations'],
    'validations_kri': ['Validations - KRI', 'KRI', 'KRI Validations'],
    'kri_master': ['KRI Master', 'KRI_Master', 'KRIMaster']  # Optional
}

# Note: Output file names are now dynamically generated from Card Name
# Using get_output_file_names() function from excel_to_json_transformer
# Example: Card "12/31/2024 Canada Annual" generates:
#   - JSON 1: 2024-12-31CanadaAnnual.json
#   - JSON 2: 2024-12-31CanadaAnnualkri.json
#   - JSON 3: 2024-12-31CanadaAnnualkri-fund.json
#   - JSON 4: 2024-12-31CanadaAnnualstrategy.json
#   - JSON 5: 2024-12-31CanadaAnnualkri-simple.json


# =============================================================================
# Sheet Finder
# =============================================================================

def find_sheet(reader: ExcelReader, patterns: List[str]) -> Optional[str]:
    """
    Find a sheet that matches any of the given patterns.
    
    Args:
        reader: ExcelReader instance
        patterns: List of patterns to search for
        
    Returns:
        Matching sheet name or None
    """
    sheet_names = reader.get_sheet_names()
    
    # First try exact match
    for pattern in patterns:
        if pattern in sheet_names:
            return pattern
    
    # Then try case-insensitive contains
    for pattern in patterns:
        for sheet_name in sheet_names:
            if pattern.lower() in sheet_name.lower():
                return sheet_name
    
    return None


# =============================================================================
# Column Name Normalization
# =============================================================================

def normalize_column_names(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize column names to handle variations in Excel headers.
    
    Args:
        records: List of row dictionaries
        
    Returns:
        Records with normalized column names
    """
    if not records:
        return records
    
    # Column name mappings (lowercase key -> standard name)
    column_mappings = {
        'card name': 'Card Name',
        'card': 'Card',
        'fund': 'Fund',
        'fund id': 'Fund ID',
        'fund id_new': 'Fund ID_New',
        'fund_id_new': 'Fund ID_New',
        'fund name_new': 'Fund Name_New',
        'fund_name_new': 'Fund Name_New',
        'trust': 'Trust',
        'trust_new': 'Trust_New',
        'group': 'Group',
        'group_new': 'Group_New',
        'book': 'Book',
        'book_new': 'Book_New',
        'fund type': 'Fund Type',
        'priority': 'Priority',
        'workflow status': 'Workflow Status',
        'validation status': 'Validation Status',
        'validation': 'Validation',
        'statement type': 'Statement Type',
        'section': 'Section',
        'line item description': 'Line Item Description',
        'control procedures': 'Control Procedures',
        'share class': 'Share Class',
        'control value': 'Control Value',
        'fs value': 'FS Value',
        'variance': 'Variance',
        'bps impact': 'BPS Impact',
        'auto / manual': 'Auto / Manual',
        'auto/manual': 'Auto / Manual',
        'validation source': 'Validation Source',
        'validation type': 'Validation Type',
        'control draft number': 'Control Draft Number',
        'test draft number': 'Test Draft Number',
        'is final': 'Is Final',
        'threshold amount': 'Threshold Amount',
        'threshold desc': 'Threshold Desc',
        'threshold percent (%)': 'Threshold Percent (%)',
        'threshold percent': 'Threshold Percent (%)',
        'threshold abs': 'Threshold Abs',
        'kri variable key1': 'KRI Variable Key1',
        'kri variable value1': 'KRI Variable Value1',
        'kri variable key2': 'KRI Variable Key2',
        'kri variable value2': 'KRI Variable Value2',
        'kri variable key3': 'KRI Variable Key3',
        'kri variable value3': 'KRI Variable Value3',
        'kri variable key4': 'KRI Variable Key4',
        'kri variable value4': 'KRI Variable Value4',
        'kri variable key5': 'KRI Variable Key5',
        'kri variable value5': 'KRI Variable Value5',
        'kri id': 'KRI ID',
        'kri name': 'KRI Name',
        'kri desc': 'KRI Desc',
        'threshold': 'Threshold',
        'validation id': 'Validation ID',
        'fiscal_year_end': 'fiscal_year_end',
        'reporting_cycle': 'reporting_cycle',
        'open_end_close_end': 'open_end_close_end',
        'reporting_date': 'reporting_date',
        'status': 'Status',
        '#': '#',
        'comments': 'Comments',
        'comment details': 'Comment Details',
    }
    
    normalized = []
    for record in records:
        new_record = {}
        for key, value in record.items():
            # Find normalized key
            key_lower = str(key).lower().strip()
            normalized_key = column_mappings.get(key_lower, key)
            new_record[normalized_key] = value
        normalized.append(new_record)
    
    return normalized


# =============================================================================
# Main Transformation Function
# =============================================================================

def run_transformation(input_file: str, output_folder: str, verbose: bool = True):
    """
    Run the complete transformation from Excel to JSON.
    
    Args:
        input_file: Path to the input Excel file
        output_folder: Path to the output folder
        verbose: Whether to print progress messages
    """
    start_time = datetime.now()
    
    if verbose:
        print("=" * 80)
        print("EXCEL TO JSON TRANSFORMATION")
        print("=" * 80)
        print(f"\nInput File:  {input_file}")
        print(f"Output Folder: {output_folder}")
        print()
    
    # Validate input file
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Read Excel file
    if verbose:
        print("Step 1: Reading Excel file...")
    
    reader = ExcelReader(input_file)
    sheet_names = reader.get_sheet_names()
    
    if verbose:
        print(f"  Found {len(sheet_names)} sheets: {sheet_names}")
    
    # Find required sheets
    cards_sheet = find_sheet(reader, SHEET_CONFIG['cards'])
    funds_sheet = find_sheet(reader, SHEET_CONFIG['funds'])
    trimmed_sheet = find_sheet(reader, SHEET_CONFIG['validations_trimmed'])
    kri_sheet = find_sheet(reader, SHEET_CONFIG['validations_kri'])
    kri_master_sheet = find_sheet(reader, SHEET_CONFIG['kri_master'])  # Optional
    
    if verbose:
        print(f"\n  Matched sheets:")
        print(f"    Cards: {cards_sheet or 'NOT FOUND'}")
        print(f"    Funds: {funds_sheet or 'NOT FOUND'}")
        print(f"    Validations-TRIMMED: {trimmed_sheet or 'NOT FOUND'}")
        print(f"    Validations-KRI: {kri_sheet or 'NOT FOUND'}")
        print(f"    KRI Master: {kri_master_sheet or '(Optional - not found)'}")
    
    # Validate required sheets exist
    missing_sheets = []
    if not cards_sheet:
        missing_sheets.append('Cards')
    if not funds_sheet:
        missing_sheets.append('Funds')
    if not trimmed_sheet:
        missing_sheets.append('Validations-TRIMMED')
    if not kri_sheet:
        missing_sheets.append('Validations-KRI')
    
    if missing_sheets:
        raise ValueError(f"Missing required sheets: {missing_sheets}")
    
    # Read data from sheets
    if verbose:
        print("\nStep 2: Loading data from sheets...")
    
    cards_data = normalize_column_names(reader.read_sheet(cards_sheet))
    funds_data = normalize_column_names(reader.read_sheet(funds_sheet))
    trimmed_data = normalize_column_names(reader.read_sheet(trimmed_sheet))
    kri_data = normalize_column_names(reader.read_sheet(kri_sheet))
    
    kri_master_data = []
    if kri_master_sheet:
        kri_master_data = normalize_column_names(reader.read_sheet(kri_master_sheet))
    
    if verbose:
        print(f"    Cards: {len(cards_data)} records")
        print(f"    Funds: {len(funds_data)} records")
        print(f"    Validations-TRIMMED: {len(trimmed_data)} records")
        print(f"    Validations-KRI: {len(kri_data)} records")
        if kri_master_data:
            print(f"    KRI Master: {len(kri_master_data)} records")
    
    # Create transformer and load data
    if verbose:
        print("\nStep 3: Transforming data...")
    
    transformer = ExcelToJSONTransformer()
    transformer.load_cards(cards_data)
    transformer.load_funds(funds_data)
    transformer.load_validations_trimmed(trimmed_data)
    transformer.load_validations_kri(kri_data)
    
    if kri_master_data:
        transformer.load_kri_master(kri_master_data)
    
    # Transform
    outputs = transformer.transform()
    
    if verbose:
        print("  Transformation complete!")
    
    # Get card names for dynamic file naming
    # File names are auto-generated from Cards tab using Card Name column
    # For each Card Name, 5 files are created with the card name as prefix
    card_names = []
    for card_record in cards_data:
        card_name = card_record.get('Card Name', '')
        if card_name and card_name not in card_names:
            card_names.append(card_name)
    
    if not card_names:
        # Fallback if no card names found
        card_names = ['output']
    
    # Write output files for each card
    if verbose:
        print("\nStep 4: Writing output files...")
        print(f"  Cards found: {len(card_names)}")
        print(f"  Files per card: 5")
        print(f"  Total files to create: {len(card_names) * 5}")
    
    all_output_paths = {}
    
    for card_name in card_names:
        # Generate dynamic file names based on Card Name
        file_names = get_output_file_names(card_name)
        
        if verbose:
            print(f"\n  Card: {card_name}")
        
        card_outputs = {}
        for key in ['json1', 'json2', 'json3', 'json4', 'json5']:
            filename = file_names[key]
            output_path = os.path.join(output_folder, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(outputs[key])
            card_outputs[key] = output_path
            if verbose:
                print(f"    • {filename}")
        
        all_output_paths[card_name] = card_outputs
    
    # Print summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if verbose:
        print("\n" + "=" * 80)
        print("TRANSFORMATION COMPLETE")
        print("=" * 80)
        print(f"\nDuration: {duration:.2f} seconds")
        print(f"\nOutput files created in: {output_folder}")
        
        for card_name in card_names:
            file_names = get_output_file_names(card_name)
            print(f"\n  {card_name}:")
            for key in ['json1', 'json2', 'json3', 'json4', 'json5']:
                print(f"    • {file_names[key]}")
        
        # Print statistics
        json1 = json.loads(outputs['json1'])
        json2 = json.loads(outputs['json2'])
        json3 = json.loads(outputs['json3'])
        
        print(f"\nStatistics:")
        print(f"  Total Validations: {json1['data']['getValidations']['rowCount']}")
        print(f"  Unique KRI Types: {len(json2['data']['kriDetails'])}")
        print(f"  Funds Processed: {len(json3['data']['fundKriStatusCount'])}")
    
    return all_output_paths


# =============================================================================
# Command Line Interface
# =============================================================================

def main():
    """Main entry point for command line execution."""
    parser = argparse.ArgumentParser(
        description='Transform Excel data to JSON format for KRI Validations system.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_transformation.py --input data.xlsx --output ./output
  python run_transformation.py -i "C:\\Data\\input.xlsx" -o "C:\\Data\\output"
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Path to the input Excel file'
    )
    
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Path to the output folder'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )
    
    args = parser.parse_args()
    
    try:
        run_transformation(
            input_file=args.input,
            output_folder=args.output,
            verbose=not args.quiet
        )
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
