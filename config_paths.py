#!/usr/bin/env python3
"""
Configuration file for input and output paths.
Update these paths according to your environment.
"""

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

# Input Excel file path
INPUT_FILE = r"C:\Users\ZF231ZS\OneDrive - EY\Desktop\Demo_Auto_Input\FR Demo Data Requirements.xlsx"

# Output folder path
OUTPUT_FOLDER = r"C:\Users\ZF231ZS\OneDrive - EY\Desktop\Demo_Auto_Output"

# =============================================================================
# SHEET NAME CONFIGURATION (Optional - override if your Excel has different names)
# =============================================================================

# These are patterns to match sheet names in the Excel file
# The transformer will look for sheets containing these patterns (case-insensitive)

SHEET_PATTERNS = {
    'cards': ['Cards', 'Card'],
    'funds': ['Funds', 'Fund'],
    'validations_trimmed': ['Validations - TRIMMED', 'TRIMMED', 'Trimmed', 'Normal Validations'],
    'validations_kri': ['Validations - KRI', 'KRI', 'KRI Validations'],
    'kri_master': ['KRI Master', 'KRI_Master', 'KRIMaster']  # Optional
}

# =============================================================================
# OUTPUT FILE NAMES
# =============================================================================

OUTPUT_FILE_NAMES = {
    'json1': 'validations_combined.json',
    'json2': 'kri_details.json', 
    'json3': 'fund_kri_status.json',
    'json4': 'strategy_kri_count.json',
    'json5': 'kri_simple.json'
}
