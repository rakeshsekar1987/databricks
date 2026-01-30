# Excel to JSON Transformation Framework

A data-driven framework for transforming Excel data into JSON format for KRI (Key Risk Indicator) Validations system.

## Features

- **Data-Driven**: All mappings are derived from input data - no hardcoding
- **Flexible**: Supports optional KRI Master sheet for pre-defined IDs
- **Comprehensive**: Generates 5 JSON output files from 4 Excel input tabs
- **Validated**: Includes 216 automated tests

## Quick Start

### 1. Install Dependencies

```bash
pip install pandas openpyxl
```

### 2. Configure Paths

Edit `config_paths.py` with your input and output paths:

```python
INPUT_FILE = r"C:\Users\ZF231ZS\OneDrive - EY\Desktop\Demo_Auto_Input\FR Demo Data Requirements.xlsx"
OUTPUT_FOLDER = r"C:\Users\ZF231ZS\OneDrive - EY\Desktop\Demo_Auto_Output"
```

### 3. Run the Transformation

**Option A: Double-click the batch file (Windows)**
```
run.bat
```

**Option B: Run from command line**
```bash
python main.py
```

**Option C: Specify paths directly**
```bash
python run_transformation.py --input "path/to/input.xlsx" --output "path/to/output"
```

## Input Excel Structure

Your Excel file should have these tabs:

| Tab Name | Description |
|----------|-------------|
| **Cards** | Report/card definitions with Card Name as primary key |
| **Funds** | Fund master data with Fund ID_New as primary key |
| **Validations - TRIMMED** | Normal validation records |
| **Validations - KRI** | KRI validation records with KRI Variable columns |
| **KRI Master** (Optional) | Pre-defined KRI IDs and thresholds |

### Required Columns

**Cards Tab:**
- Card Name, fiscal_year_end, reporting_cycle, open_end_close_end, reporting_date, Status

**Funds Tab:**
- #, Trust, Trust_New, Fund, Fund ID, Fund Name_New, Fund ID_New, Group, Group_New, Book, Book_New, Fund Type

**Validations Tabs:**
- Card, Fund, Priority, Workflow Status, Validation Status, Validation, Statement Type, Section, Line Item Description, Control Procedures, Share Class, Control Value, FS Value, Variance, BPS Impact, Auto / Manual, Validation Source, Validation Type, Control Draft Number, Test Draft Number, Is Final, Threshold columns

**Validations - KRI Tab (Additional):**
- KRI Variable Key1-5, KRI Variable Value1-5

## Output Files

| File | Description |
|------|-------------|
| `validations_combined.json` | Combined validations from TRIMMED and KRI tabs |
| `kri_details.json` | KRI details grouped by KRI type with fund details |
| `fund_kri_status.json` | Fund KRI status counts and filters |
| `strategy_kri_count.json` | Strategy-level KRI aggregation |
| `kri_simple.json` | Simple KRI details list for filtering |

## Key Data Mappings

### Cross-References
- `Validations.Fund` → `Funds.Fund ID_New` (lookup for trust, book, group)

### Derived Fields
- **group**: From Group_New column in Funds tab (Fund ID_New is lookup key)
- **validationDesc**: Control Procedures for KRI, Validation for non-KRI
- **valuesUsedInFormula**: Built from KRI Variable Key/Value columns

### Calculations
- **rowCount**: COUNT(TRIMMED) + COUNT(KRI)
- **kriTotalCount**: COUNT(DISTINCT KRI names)
- **kriStatusCount**: COUNT(KRI per fund)

### Business-Provided Values (from KRI Master)
- **risk**: Business-provided from KRI Master (NOT calculated from BPS Impact)
- **threshold**: Business-provided from KRI Master (unique per KRI)
- **riskThresholds**: Business-provided risk threshold definitions (optional)

## Files in This Repository

| File | Description |
|------|-------------|
| `main.py` | Main entry point |
| `run_transformation.py` | Transformation orchestration |
| `excel_to_json_transformer.py` | Core transformation logic |
| `excel_reader.py` | Excel file reading utility |
| `config_paths.py` | Path configuration |
| `run.bat` | Windows batch file |
| `requirements.txt` | Python dependencies |
| `qa_validation.py` | Comprehensive test suite |

## Running Tests

```bash
python qa_validation.py
```

This runs 216 tests covering all field mappings, calculations, and cross-references.

## Troubleshooting

### "Module not found" Error
Make sure you've installed the dependencies:
```bash
pip install pandas openpyxl
```

### "Sheet not found" Error
Check that your Excel file has the required tabs. The framework looks for:
- A tab containing "Cards" or "Card"
- A tab containing "Funds" or "Fund"
- A tab containing "TRIMMED" or "Validations - TRIMMED"
- A tab containing "KRI" or "Validations - KRI"

### Number Parsing Issues
The framework handles Indian number format (7,98,606.00) and standard format (798,606.00).

## License

Internal use only - EY
