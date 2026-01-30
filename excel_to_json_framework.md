# Excel to JSON Transformation Framework - Data-Driven Version

## Overview

This framework defines the transformation rules for converting Excel data into 5 JSON output files for KRI (Key Risk Indicator) Validations system. **All mappings and relationships are derived from the input data - no hardcoding.**

---

## Output File Naming Convention

File names are derived from the **Card Name** column:

| Card Name | Transformation | Output File Names |
|-----------|----------------|-------------------|
| `12/31/2024 Canada Annual` | Date to ISO + Clean text | `2024-12-31CanadaAnnual.json` |

### File Name Pattern
```
{YYYY-MM-DD}{CardNameClean}{Suffix}.json
```

### All 5 Output Files for Each Card
| JSON | Suffix | Example File Name |
|------|--------|-------------------|
| JSON 1 | (none) | `2024-12-31CanadaAnnual.json` |
| JSON 2 | `kri` | `2024-12-31CanadaAnnualkri.json` |
| JSON 3 | `kri-fund` | `2024-12-31CanadaAnnualkri-fund.json` |
| JSON 4 | `strategy` | `2024-12-31CanadaAnnualstrategy.json` |
| JSON 5 | `-krisimple` | `2024-12-31CanadaAnnual-krisimple.json` |

---

## Input Data Structure

### Required Excel Tabs (4 tabs):

| Tab | Purpose | Key Columns |
|-----|---------|-------------|
| **Cards** | Report/card definitions | Card Name (Primary Key) |
| **Funds** | Fund master data | Fund ID_New (Primary Key for lookups) |
| **Validations - TRIMMED** | Normal validation records | Card, Fund (Foreign Keys) |
| **Validations - KRI** | KRI validation records | Card, Fund, KRI Variables 1-5 |

### KRI Master Tab (Required for Business-Provided Values)

| Tab | Purpose | Key Columns |
|-----|---------|-------------|
| **KRI Master** | KRI IDs, thresholds, and risk levels | KRI ID, KRI Name, Validation ID, Risk, Threshold |

**KRI Master Columns:**
- `KRI ID`: Unique identifier - **NOT sequential** (e.g., "KRI_1", "KRI_6", "KRI_55")
- `KRI Name`: Name matching Validations-KRI.Validation column
- `Validation ID`: Pre-defined validation ID (e.g., 999991, 999996, 999999)
- `Threshold`: Business-provided threshold rules as JSON - **UNIQUE per KRI**
- `Risk`: Business-provided risk level - **NOT calculated from BPS Impact**
- `Risk Thresholds`: Optional risk threshold definitions as JSON

**Example KRI Master Data:**
| KRI ID | KRI Name | Validation ID | Risk | Threshold |
|--------|----------|---------------|------|-----------|
| KRI_1 | Interest Expense vs Average Borrowings | 999991 | High | `{"High":">7%",...}` |
| KRI_6 | Defaulted Securities Review | 999996 | Medium | `{"High":">5%",...}` |
| KRI_55 | Effective Leverage: YoY Change | 999999 | Low | `{"High":">10%",...}` |

**IMPORTANT - Risk Does NOT Correlate with BPS:**
- BPS 1.53 → "High" (business decision)
- BPS 0 → "Medium" (business decision)
- BPS 116.87 → "Low" (business decision - high BPS can map to Low!)

---

## Data-Driven Relationships

### 1. Cross-Reference: Validations → Funds

```
Validations.Fund  ──────────────────►  Funds.Fund ID_New
                                              │
                                              ├── Trust_New    → JSON trust
                                              ├── Book_New     → JSON book, fundName
                                              ├── Fund Name_New→ JSON fundName (in JSON3)
                                              └── Fund ID_New  → Derive Group Letter
```

**How Group is Derived:**
- Group is taken DIRECTLY from the `Group_New` column in the Funds tab
- Fund ID_New is used as the lookup key to find the correct fund record
- Example: If CAN2 has Group_New = "B", then JSON group = "B"

### 2. Cross-Reference: Validations → Cards

```
Validations.Card  ──────────────────►  Cards.Card Name
                                              │
                                              └── (Used for context/filtering)
```

### 3. KRI ID Generation (Data-Driven)

**Option A: With KRI Master Tab (Recommended)**
```
Validations-KRI.Validation ──────►  KRI Master.KRI Name
                                           │
                                           ├── KRI ID        → JSON kriId
                                           ├── Validation ID → JSON validationId
                                           └── Threshold     → JSON threshold
```

**Option B: Without KRI Master Tab (Auto-Generate)**
```
KRI validations are processed in order:
  1st KRI encountered → KRI_1, validationId: 999991
  2nd KRI encountered → KRI_2, validationId: 999992
  3rd KRI encountered → KRI_3, validationId: 999993
  ...
```

### 4. Merge Operation

```
Validations-TRIMMED ────┐
                        ├───► Combined Validations List (JSON 1)
Validations-KRI ────────┘
```

---

## Field Mapping Rules (All Data-Driven)

### JSON 1: Combined Validations

| JSON Field | Source | Derivation Method |
|------------|--------|-------------------|
| **id** | Generated | Hash of card + fund + validation + index |
| **validationId** | Auto-generated | Row order (TRIMMED) or KRI Master lookup |
| **trust** | Funds.Trust_New | Cross-reference via Validations.Fund |
| **group** | Funds.Group_New | Direct from Group_New column (Fund ID_New is lookup key) |
| **book** | Funds.Book_New | Cross-reference via Validations.Fund |
| **fund** | Validations.Fund | Direct from Excel |
| **fundCode** | Validations.Fund | Same as fund |
| **validation** | Validations.Validation | Direct from Excel |
| **priority** | Validations.Priority | Direct from Excel |
| **validationStatus** | Validations.Validation Status | Direct from Excel |
| **controlValue** | Validations.Control Value | Parse as number |
| **fsValue** | Validations.FS Value | Parse as number (remove commas) |
| **variance** | Validations.Variance | Parse as number |
| **bpsImpact** | Validations.BPS Impact | Parse as number |
| **statementType** | Validations.Statement Type | Direct from Excel |
| **section** | Validations.Section | Direct from Excel |
| **lineItemDescription** | Validations.Line Item Description | Direct from Excel |
| **validationType** | Validations.Validation Type | Direct from Excel |
| **validationSource** | Validations.Validation Source | Direct from Excel |
| **autoManual** | Validations.Auto / Manual | Direct from Excel |
| **webappWorkflowStatus** | Validations.Workflow Status | Direct from Excel |
| **controlDraftNumber** | Validations.Control Draft Number | Extract integer part |
| **validationDesc** | Control Procedures or Validation | Clean text |
| **valuesUsedInFormula** | KRI Variables 1-5 | Build JSON from key-value pairs |
| **rowCount** | Calculated | COUNT(TRIMMED) + COUNT(KRI) |

### JSON 2: KRI Details

| JSON Field | Source | Derivation Method |
|------------|--------|-------------------|
| **kriName** | Validations-KRI.Validation | Direct from Excel |
| **kriId** | KRI Master or Generated | Lookup or sequential |
| **kriDesc** | Validations-KRI.Control Procedures | Clean text |
| **threshold** | KRI Master.Threshold | Business-provided unique values per KRI |
| **fundDetails[].fundCode** | Validations-KRI.Fund | Direct from Excel |
| **fundDetails[].fundName** | Funds.Book_New | Cross-reference |
| **fundDetails[].result** | Validations-KRI.BPS Impact | As string |
| **fundDetails[].risk** | KRI Master.Risk | Business-provided (NOT calculated from BPS) |
| **fundDetails[].validationStatus** | Validations-KRI.Validation Status | Direct from Excel |
| **fundDetails[].valuesUsedInFormula** | KRI Variables 1-5 | Build JSON |

### JSON 3: Fund KRI Status Count

| JSON Field | Source | Derivation Method |
|------------|--------|-------------------|
| **fundKriStatusCount[].fundCode** | Funds.Fund ID_New | Iterate all funds |
| **fundKriStatusCount[].fundName** | Funds.Fund Name_New | From Funds tab |
| **fundKriStatusCount[].kriTotalCount** | Calculated | COUNT(DISTINCT KRI names) |
| **fundKriStatusCount[].kriStatusCount** | Calculated | COUNT(KRI WHERE Fund = fundCode) |
| **kriFilter[]** | Validations-KRI | Distinct KRI types |

### JSON 4: Strategy KRI Count

| JSON Field | Source | Derivation Method |
|------------|--------|-------------------|
| **kriTotalCount** | Calculated | COUNT(DISTINCT KRI names) |
| **kriStatusCount** | Calculated | COUNT(ALL KRI validations) |

### JSON 5: KRI Simple Details

| JSON Field | Source | Derivation Method |
|------------|--------|-------------------|
| **kriDetails[]** | Validations-KRI | Distinct KRI types with IDs |

---

## Calculation Formulas

### Row Count (JSON 1)
```
rowCount = len(Validations_TRIMMED) + len(Validations_KRI)
```

### KRI Total Count (JSON 3, 4)
```
kriTotalCount = len(DISTINCT(Validations_KRI.Validation))
```

### KRI Status Count per Fund (JSON 3)
```python
for each fund in Funds:
    kriStatusCount[fund] = COUNT(Validations_KRI WHERE Fund == fund.Fund_ID_New)
```

### Risk (JSON 2) - Business-Provided

**IMPORTANT**: Risk is NOT calculated from BPS Impact. It is provided by the business team in the KRI Master sheet.

```python
def get_risk(kri_name, kri_master):
    # Look up risk from business-provided KRI Master data
    # Returns the Risk column value for this KRI
    kri = find_kri_by_name(kri_master, kri_name)
    if kri:
        return kri['Risk']  # Business-provided value (e.g., "Low", "Medium", "High")
    return ''  # No hardcoded default
```

**Example Business Mapping:**
- BPS Impact = 0 → "Medium" (business decision, not calculated)
- Risk Thresholds: `{"Green": "<2%", "Yellow": "2% - 5%", "Red": ">5%"}`

The business team provides:
- `Risk`: The risk level for each KRI (e.g., "Low", "Medium", "High")
- `Risk Thresholds`: JSON string defining threshold rules (optional)

### Group Letter Derivation
```python
def get_group(fund_id_new, funds_data):
    # Look up the fund by Fund ID_New and return the Group_New value
    fund = find_fund_by_id(funds_data, fund_id_new)
    if fund:
        return fund['Group_New']  # Use Group_New directly
    return ''
```

### valuesUsedInFormula Construction
```python
def build_values_used_in_formula(row):
    result = OrderedDict()
    for i in range(1, 6):
        key = row[f'KRI Variable Key{i}']
        value = row[f'KRI Variable Value{i}']
        if key and key not in ['', '--']:
            result[key] = parse_number(value)
    return json.dumps(result) if result else ""
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXCEL INPUT                                     │
├─────────────┬─────────────┬─────────────────┬─────────────┬─────────────────┤
│   Cards     │   Funds     │ Validations-    │ Validations-│  KRI Master     │
│   Tab       │    Tab      │    TRIMMED      │     KRI     │  (Optional)     │
└──────┬──────┴──────┬──────┴────────┬────────┴──────┬──────┴────────┬────────┘
       │             │               │               │               │
       ▼             ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA LOOKUP SERVICE                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ INDEXES BUILT FROM DATA:                                                │ │
│  │ • Fund Index: Fund ID_New → Fund details                                │ │
│  │ • Card Index: Card Name → Card details                                  │ │
│  │ • KRI Index: KRI Name → KRI ID, Validation ID (from KRI Master)         │ │
│  │                                                                         │ │
│  │ DERIVED MAPPINGS:                                                       │ │
│  │ • Group Letters: Extracted from Fund ID_New pattern                     │ │
│  │ • KRI IDs: Sequential order or from KRI Master                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
       ┌────────────┬───────────────┼───────────────┬────────────┐
       ▼            ▼               ▼               ▼            ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│  JSON 1   │ │  JSON 2   │ │  JSON 3   │ │  JSON 4   │ │  JSON 5   │
│ Combined  │ │   KRI     │ │ Fund KRI  │ │ Strategy  │ │   KRI     │
│Validations│ │  Details  │ │  Status   │ │   Count   │ │  Simple   │
└───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘
```

---

## Excel Column Reference

### Cards Tab
| Column Name | JSON Field | Notes |
|-------------|------------|-------|
| Card Name | - | Primary key for card lookup |
| fiscal_year_end | - | Metadata |
| reporting_cycle | - | Metadata |
| open_end_close_end | - | Category filter |
| reporting_date | - | Metadata |
| Status | - | Processing status |

### Funds Tab
| Column Name | JSON Field | Notes |
|-------------|------------|-------|
| # | - | Row number |
| Trust | - | Original trust name |
| **Trust_New** | trust | → JSON trust field |
| Fund | - | Full fund name |
| Fund ID | - | Original fund ID |
| **Fund Name_New** | fundName (JSON3) | Display name for fund |
| **Fund ID_New** | fund, fundCode | **Primary key for lookups**, derives group |
| Group | - | Original group |
| Group_New | - | (Not used, group derived from Fund ID) |
| Book | - | Original book |
| **Book_New** | book, fundName (JSON2) | Book/fund display name |
| Fund Type | - | Category (Canada, OEF, CEF, etc.) |

### Validations Tabs (TRIMMED & KRI)
| Column Name | JSON Field | Notes |
|-------------|------------|-------|
| Card | - | Links to Cards tab |
| **Fund** | fund, fundCode | **Foreign key to Funds.Fund ID_New** |
| Priority | priority | Material/Standard |
| Workflow Status | webappWorkflowStatus | Current workflow state |
| Validation Status | validationStatus | Passed/Failed |
| Validation | validation | Validation rule name |
| Statement Type | statementType | SCF/SOA/KRI/etc. |
| Section | section | Section description |
| Line Item Description | lineItemDescription | Details |
| Control Procedures | validationDesc (KRI) | Formula description |
| Share Class | shareClass | Usually empty |
| Control Value | controlValue | Numeric |
| FS Value | fsValue | Numeric (parse commas) |
| Variance | variance | Numeric |
| BPS Impact | bpsImpact | Numeric, result field in fundDetails (risk is business-provided) |
| Auto / Manual | autoManual | Processing type |
| Validation Source | validationSource | Source system |
| Validation Type | validationType | Type classification |
| Control Draft Number | controlDraftNumber | Extract integer |
| Test Draft Number | testDraftNumber | Draft version |
| Is Final | isFinalDraft | Boolean |
| Threshold Amount | thresholdColAmount | Threshold value |
| Threshold Desc | thresholdColDesc | Threshold description |
| Threshold Percent (%) | thresholdPercent | Percentage |
| Threshold Abs | thresholdAbs | Absolute value |
| KRI Variable Key1-5 | valuesUsedInFormula | Build JSON object |
| KRI Variable Value1-5 | valuesUsedInFormula | Build JSON object |

### KRI Master Tab (Optional)
| Column Name | JSON Field | Notes |
|-------------|------------|-------|
| KRI ID | kriId | Pre-defined KRI identifier |
| KRI Name | - | Must match Validations.Validation |
| KRI Desc | kriDesc | KRI description |
| Threshold | threshold | JSON threshold definition (business-provided) |
| Validation ID | validationId | Pre-defined validation ID |
| Risk | fundDetails[].risk | Business-provided risk level (NOT calculated from BPS) |
| Risk Thresholds | - | Business-provided risk threshold definitions (JSON) |

---

## Key Principles

1. **No Hardcoded Mappings**: All mappings come from data
2. **Cross-Reference by Keys**: Use Fund ID_New and Card Name as keys
3. **Business-Provided Values**: Risk, threshold, and group come from Excel data (not calculated)
4. **Optional Master Data**: KRI Master provides KRI IDs, thresholds, and risk levels
5. **Order Matters**: KRI IDs generated based on order encountered (if no KRI Master)
6. **Consistent IDs**: Same validation uses same ID across all JSONs

### What is Business-Provided (NOT Calculated):
- **Group**: Comes from `Group_New` column in Funds tab
- **Threshold**: Comes from `Threshold` column in KRI Master
- **Risk**: Comes from `Risk` column in KRI Master (NOT calculated from BPS Impact)

---

## Example: Data Derivation

Given this Funds data:
```
Fund ID_New: CAN1, CAN2, CAN3
Trust_New: Canada, Canada, Canada
Book_New: Income Strategy Fund, Credit Income Fund, International Bond Trust
```

**Derived mappings:**
```
CAN1 → group: A (1st letter)
CAN2 → group: B (2nd letter)
CAN3 → group: C (3rd letter)
```

Given this KRI data (in order):
```
1. Interest Expense versus Average Borrowings
2. Defaulted Securities Review
3. Effective Leverage: Year Over Year Change
```

**With KRI Master:**
```
Interest Expense... → KRI_1, validationId: 999991
Defaulted Securities... → KRI_6, validationId: 999996
Effective Leverage... → KRI_9A, validationId: 999999
```

**Without KRI Master (auto-generated):**
```
Interest Expense... → KRI_1, validationId: 999991
Defaulted Securities... → KRI_2, validationId: 999992
Effective Leverage... → KRI_3, validationId: 999993
```
