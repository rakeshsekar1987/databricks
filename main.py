#!/usr/bin/env python3
"""
Main Script - Excel to JSON Transformation

This script reads the configuration from config_paths.py and runs the transformation.

Usage:
    python main.py
    
Or with command line arguments:
    python main.py --input "path/to/input.xlsx" --output "path/to/output"
"""

import sys
import os
import argparse

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_transformation import run_transformation

# Import default paths from config
try:
    from config_paths import INPUT_FILE, OUTPUT_FOLDER
except ImportError:
    INPUT_FILE = None
    OUTPUT_FOLDER = None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Excel to JSON Transformation for KRI Validations',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-i', '--input',
        default=INPUT_FILE,
        help='Path to input Excel file (default from config_paths.py)'
    )
    
    parser.add_argument(
        '-o', '--output', 
        default=OUTPUT_FOLDER,
        help='Path to output folder (default from config_paths.py)'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )
    
    args = parser.parse_args()
    
    # Validate paths
    if not args.input:
        print("Error: No input file specified.")
        print("Either set INPUT_FILE in config_paths.py or use --input argument")
        return 1
    
    if not args.output:
        print("Error: No output folder specified.")
        print("Either set OUTPUT_FOLDER in config_paths.py or use --output argument")
        return 1
    
    # Run transformation
    try:
        run_transformation(
            input_file=args.input,
            output_folder=args.output,
            verbose=not args.quiet
        )
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
