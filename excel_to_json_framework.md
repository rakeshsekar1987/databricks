# Excel to JSON Transformation Framework

## Overview

This framework defines the transformation rules for converting 4 Excel tabs into 5 JSON output files for KRI (Key Risk Indicator) Validations system.

---

## Input Data Structure

### Excel Tab 1: Cards
| Column | Description | Key Role |
|--------|-------------|----------|
| Card Name | Unique identifier for the card/report | Primary Key - Links to Validations |
| fiscal_year_end | Fiscal year end date | Metadata |
| reporting_cycle | Annual/Quarterly/etc. | Metadata |
| open_end_close_end | Fund type category (Canada, OEF, CEF, etc.) | Category filter |
| reporting_date | Actual reporting date | Metadata |
| Status | Processing status | Metadata |

### Excel Tab 2: Funds
| Column | Description | Key Role |
|--------|-------------|----------|
| # | Row number | Reference |
| Trust / Trust_New | Trust name | → JSON `trust` field |
| Fund | Full fund name | Display name |
| Fund ID / Fund ID_New | Fund code (e.g., CAN1, CAN2) | **Foreign Key** - Links to Validations.Fund |
| Fund Name_New | Renamed fund display name | → JSON `fundName`, `book` |
| Group / Group_New | Group code (H, G → mapped to A, B, C) | → JSON `group` (with mapping) |
| Book / Book_New | Book name | → JSON `book` |
| Fund Type | Type of fund (Canada, OEF, CEF) | Category |
| Card columns (12/31/2024...) | X marks which cards apply | Card-Fund mapping |

### Excel Tab 3: Validations - TRIMMED (Normal Validations)
| Column | Description | Key Role |
|--------|-------------|----------|
| Card | Card reference | Links to Cards tab |
| Fund | Fund ID code | **Foreign Key** - Links to Funds.Fund ID_New |
| Priority | Material/Standard | → JSON `priority` |
| Workflow Status | Current workflow state | → JSON `webappWorkflowStatus` |
| Validation Status | Passed/Failed | → JSON `validationStatus` |
| Validation | Validation rule name | → JSON `validation`, `validationDesc` |
| Statement Type | SCF/SOA/KRI/etc. | → JSON `statementType` |
| Section | Section description | → JSON `section` |
| Line Item Description | Line item details | → JSON `lineItemDescription` |
| Control Value | Control calculated value | → JSON `controlValue` |
| FS Value | Financial statement value | → JSON `fsValue` |
| Variance | Difference | → JSON `variance` |
| BPS Impact | Basis points impact | → JSON `bpsImpact` |
| Auto / Manual | Processing type | → JSON `autoManual` |
| Validation Source | Source system | → JSON `validationSource` |
| Validation Type | Type classification | → JSON `validationType` |
| Control Draft Number | Draft version | → JSON `controlDraftNumber` |
| Test Draft Number | Test version | → JSON `testDraftNumber` |
| Is Final | Boolean flag | → JSON `isFinalDraft` |
| Threshold Amount/Desc/Percent/Abs | Threshold values | → JSON threshold fields |

### Excel Tab 4: Validations - KRI
Same structure as Validations-TRIMMED, plus:
| Column | Description | Key Role |
|--------|-------------|----------|
| KRI Variable Key1-5 | KRI formula variable names | → JSON `valuesUsedInFormula` keys |
| KRI Variable Value1-5 | KRI formula variable values | → JSON `valuesUsedInFormula` values |
| Control Procedures | Formula description | → JSON `validationDesc` |

---

## Cross-Reference Relationships

```
┌─────────────┐         ┌─────────────┐
│   Cards     │◄────────│ Validations │
│  (Card Name)│  Card   │  (TRIMMED)  │
└─────────────┘         └──────┬──────┘
                               │ Fund
                               ▼
┌─────────────┐         ┌─────────────┐
│   Funds     │◄────────│ Validations │
│ (Fund ID_New)  Fund   │   (KRI)     │
└─────────────┘         └─────────────┘
```

### Key Relationships:
1. **Validations.Card** → **Cards.Card Name** (Card context lookup)
2. **Validations.Fund** → **Funds.Fund ID_New** (Fund details lookup)
3. **Validations-TRIMMED + Validations-KRI** → Merged into single validation set

---

## Auto-Generated Fields

| Field | Generation Rule | Used In |
|-------|-----------------|---------|
| `id` | SHA256-like hash (random/sequential pattern) | JSON 1 |
| `validationId` | Auto-increment or mapped ID (999991, 999996, 999999 for KRI) | JSON 1, 2, 3, 5 |
| `requestId` | UUID without hyphens (uppercase) | All JSONs |
| `auditVersionControlDs` | Always "1" | JSON 1 |
| `writeTs` | Current timestamp (YYYY-MM-DD HH:mm:ss.SSSSSSS) | JSON 1 |
| `kriId` | Mapped from validation name (KRI_1, KRI_6, KRI_9A, etc.) | JSON 2, 3, 5 |
| `rowCount` | Count of validations in response | JSON 1 |
| `kriTotalCount` | Total unique KRI types in system | JSON 3, 4 |
| `kriStatusCount` | Count of KRI validations per fund | JSON 3, 4 |

---

## Field Mapping Rules

### Group Mapping (Funds.Group_New → JSON group)
```
Source Group_New | Mapped JSON group
-----------------|-------------------
A (with CAN2)    | B
A (with CAN3)    | C
(Rule: Sequential assignment based on fund order or specific fund logic)
```

### KRI ID Mapping (Validation Name → kriId)
```
Validation Name                           | kriId
------------------------------------------|--------
Interest Expense versus Average Borrowings| KRI_1
Defaulted Securities Review               | KRI_6
Effective Leverage: Year Over Year Change | KRI_9A
```

### Priority Mapping (Validation Type → Priority)
```
Statement Type | Default Priority
---------------|------------------
KRI            | Standard (unless override)
SCF, SOA, etc. | Material/Standard (from Excel)
```

### valuesUsedInFormula Construction
```python
# For KRI Validations only
{
    "KRI Variable Key1": KRI Variable Value1,
    "KRI Variable Key2": KRI Variable Value2,
    ...
}
# Values are parsed to remove commas and convert to numbers
```

---

## JSON Output Specifications

### JSON 1: Combined Validations
**Purpose:** Unified validation response with all validations (TRIMMED + KRI)

**Structure:**
```json
{
    "requestDetails": { "requestId": "<auto-generated>" },
    "data": {
        "getValidations": {
            "rowCount": <count of validations>,
            "pageInfo": { "hasNextPage": false, "hasPreviousPage": false },
            "validations": [ <array of validation objects> ]
        }
    }
}
```

**Field Sources for each validation:**
| JSON Field | Source | Transformation |
|------------|--------|----------------|
| id | Auto-generated | Random hash pattern |
| trust | Funds.Trust_New (via Fund lookup) | Direct |
| fund | Validations.Fund | Direct |
| fundCode | Validations.Fund | Same as fund |
| group | Funds.Group_New (via Fund lookup) | Mapped (A→B, A→C based on fund) |
| book | Funds.Book_New (via Fund lookup) | Direct |
| shareClass | Validations.Share Class | Direct (often empty) |
| section | Validations.Section | Direct |
| validation | Validations.Validation | Direct |
| controlValue | Validations.Control Value | Numeric |
| fsValue | Validations.FS Value | Numeric (remove commas) |
| variance | Validations.Variance | Numeric |
| bpsImpact | Validations.BPS Impact | Numeric |
| validationType | Validations.Validation Type | Direct |
| validationSource | Validations.Validation Source | Direct |
| controlDraftNumber | Validations.Control Draft Number | Extract number or null |
| autoManual | Validations.Auto / Manual | Direct |
| priority | Validations.Priority | Direct |
| validationStatus | Validations.Validation Status | Direct |
| auditVersionControlDs | Auto-generated | Always "1" |
| writeTs | Auto-generated | Current timestamp |
| isFinalDraft | Validations.Is Final | Boolean |
| validationId | Auto-generated | Sequential ID |
| lineItemDescription | Validations.Line Item Description | Direct |
| statementType | Validations.Statement Type | Direct |
| testDraftNumber | Validations.Test Draft Number | Direct or empty |
| isCpoControl | Default | Always "0" |
| isCpoTest | Default | Always "0" |
| isBannerLessControl | Default | Always "0" |
| isBannerLessTest | Default | Always "0" |
| isBlueFontControl | Default | Always "0" |
| isBlueFontTest | Default | Always "0" |
| thresholdColAmount | Validations.Threshold Amount | Direct or empty |
| thresholdColDesc | Validations.Threshold Desc | Direct or empty |
| thresholdPercent | Validations.Threshold Percent | Direct or empty |
| thresholdAbs | Validations.Threshold Abs | Direct or empty |
| validationDesc | Validations.Control Procedures or Validation | Clean text |
| webappWorkflowStatus | Validations.Workflow Status | Direct |
| valuesUsedInFormula | KRI Variables 1-5 | JSON string (KRI only) |
| analyticStatus | N/A | null |
| fundStrategy | N/A | null |
| result | N/A | null |
| threshold | N/A | null |

---

### JSON 2: KRI Details
**Purpose:** Grouped KRI validations by KRI type with fund details

**Structure:**
```json
{
    "requestDetails": { "requestId": "<auto-generated>" },
    "data": {
        "kriDetails": [ <array of KRI group objects> ]
    }
}
```

**Field Sources:**
| JSON Field | Source | Transformation |
|------------|--------|----------------|
| kriName | Validations-KRI.Validation | Direct |
| kriId | Mapped | From kriName mapping table |
| kriDesc | Validations-KRI.Control Procedures | Clean multiline text |
| threshold | Default | JSON string with High/Medium/Low thresholds |
| fundDetails[].risk | Calculated | Based on bpsImpact vs thresholds |
| fundDetails[].threshold | N/A | null |
| fundDetails[].fundName | Funds.Book_New | Via Fund lookup |
| fundDetails[].fundCode | Validations-KRI.Fund | Direct |
| fundDetails[].result | Validations-KRI.BPS Impact | String format |
| fundDetails[].strategy | Default/Mapped | "Credit - Diversified Income" |
| fundDetails[].validationStatus | Validations-KRI.Validation Status | Direct |
| fundDetails[].validationId | Auto-generated | From JSON 1 mapping |
| fundDetails[].valuesUsedInFormula | KRI Variables 1-5 | JSON string |

---

### JSON 3: Fund KRI Status Count
**Purpose:** Summary counts per fund and KRI filter list

**Structure:**
```json
{
    "requestDetails": { "requestId": "<auto-generated>" },
    "data": {
        "fundKriStatusCount": [ <array of fund count objects> ],
        "kriFilter": [ <array of KRI filter objects> ],
        "statusFilter": [ <array of status strings> ]
    }
}
```

**Field Sources:**
| JSON Field | Source | Transformation |
|------------|--------|----------------|
| fundKriStatusCount[].kriTotalCount | Calculated | Total unique KRI types |
| fundKriStatusCount[].kriStatusCount | Calculated | Count of KRIs for this fund |
| fundKriStatusCount[].analyticsStatus | Default | "High" |
| fundKriStatusCount[].fundCode | Funds.Fund ID_New | All funds from Funds tab |
| fundKriStatusCount[].fundName | Funds.Fund Name_New | Via Fund lookup |
| kriFilter[].kriId | Mapped | From kriName mapping |
| kriFilter[].kriName | Validations-KRI.Validation | Distinct values |
| kriFilter[].validationId | Auto-generated | From JSON 1 mapping |
| statusFilter | Calculated | Distinct risk levels ["Low", "N/A", "High"] |

---

### JSON 4: Strategy KRI Count
**Purpose:** Aggregate KRI counts by strategy

**Structure:**
```json
{
    "requestDetails": { "requestId": "<auto-generated>" },
    "data": [ <array of strategy count objects> ]
}
```

**Field Sources:**
| JSON Field | Source | Transformation |
|------------|--------|----------------|
| kriTotalCount | Calculated | Total unique KRI types |
| kriStatusCount | Calculated | Total KRI validations across all funds |
| analyticsStatus | Default | "High" |
| strategy | Default/Mapped | "Credit - Diversified Income" |

---

### JSON 5: KRI Details Simple
**Purpose:** Simple list of KRI types for filtering

**Structure:**
```json
{
    "kriDetails": [ <array of KRI simple objects> ]
}
```

**Field Sources:**
| JSON Field | Source | Transformation |
|------------|--------|----------------|
| kriId | Mapped | From kriName mapping |
| kriName | Validations-KRI.Validation | Distinct values |
| validationId | Auto-generated | From JSON 1 mapping |

---

## Calculation Rules

### 1. rowCount (JSON 1)
```
rowCount = COUNT(Validations-TRIMMED) + COUNT(Validations-KRI)
```

### 2. kriTotalCount (JSON 3, 4)
```
kriTotalCount = COUNT(DISTINCT Validations-KRI.Validation)
```

### 3. kriStatusCount per Fund (JSON 3)
```
kriStatusCount[fundCode] = COUNT(Validations-KRI WHERE Fund = fundCode)
```

### 4. kriStatusCount Total (JSON 4)
```
kriStatusCount = COUNT(Validations-KRI)
```

### 5. valuesUsedInFormula (JSON 1, 2)
```python
def build_values_used_in_formula(row):
    result = {}
    for i in range(1, 6):
        key = row[f'KRI Variable Key{i}']
        value = row[f'KRI Variable Value{i}']
        if key and key != '':
            # Remove commas, convert to number
            result[key] = parse_number(value)
    return json.dumps(result)
```

### 6. Risk Level Calculation
```python
def calculate_risk(bps_impact):
    bps = abs(float(bps_impact))
    if bps >= 30:
        return "High"
    elif bps >= 15:
        return "Medium"
    else:
        return "Low"
```

---

## Data Flow Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                      Excel Input Files                         │
├──────────────┬──────────────┬─────────────────┬────────────────┤
│    Cards     │    Funds     │ Validations-    │ Validations-   │
│              │              │    TRIMMED      │     KRI        │
└──────┬───────┴──────┬───────┴────────┬────────┴───────┬────────┘
       │              │                │                │
       │              │     ┌──────────┴────────────────┤
       │              │     │                           │
       ▼              ▼     ▼                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   Data Transformation Layer                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 1. Load all Excel tabs                                   │ │
│  │ 2. Create Fund lookup index (Fund ID_New → Fund details) │ │
│  │ 3. Create Card lookup index (Card Name → Card details)   │ │
│  │ 4. Merge Validations (TRIMMED + KRI)                     │ │
│  │ 5. Apply cross-reference lookups                         │ │
│  │ 6. Generate auto-fields (id, validationId, timestamps)   │ │
│  │ 7. Calculate counts and aggregates                       │ │
│  │ 8. Map KRI names to KRI IDs                              │ │
│  │ 9. Build valuesUsedInFormula JSON                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
       │         │         │         │         │
       ▼         ▼         ▼         ▼         ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ JSON 1  │ │ JSON 2  │ │ JSON 3  │ │ JSON 4  │ │ JSON 5  │
│Combined │ │  KRI    │ │Fund KRI │ │Strategy │ │  KRI    │
│Validat. │ │ Details │ │ Status  │ │  Count  │ │ Simple  │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

---

## KRI ID Mapping Configuration

This mapping should be configurable and extendable:

```json
{
    "kriMappings": {
        "Interest Expense versus Average Borrowings": "KRI_1",
        "Defaulted Securities Review": "KRI_6",
        "Effective Leverage: Year Over Year Change": "KRI_9A"
    }
}
```

---

## Validation ID Generation Rules

| Validation Type | ID Range/Pattern |
|-----------------|------------------|
| Normal (TRIMMED) | Sequential (1000+) or descriptive (1161, etc.) |
| KRI Validations | 999991, 999996, 999999 pattern (high numbers) |

---

## Default Values

| Field | Default Value |
|-------|---------------|
| analyticsStatus | "High" |
| strategy | "Credit - Diversified Income" |
| risk | "Low" |
| threshold (KRI) | `{"High": ">30%", "Medium": ">=15% and <30%", "Low": "<15%"}` |
| isCpo*, isBannerLess*, isBlueFontControl/Test | "0" |
| auditVersionControlDs | "1" |
| pageInfo.hasNextPage | false |
| pageInfo.hasPreviousPage | false |

---

## Summary of Cross-References

| From | To | Key Field | Purpose |
|------|-----|-----------|---------|
| Validations.Fund | Funds.Fund ID_New | Fund code | Get trust, group, book |
| Validations.Card | Cards.Card Name | Card name | Get reporting context |
| JSON 2, 3, 5 validationId | JSON 1 validationId | validationId | Consistent IDs |
| JSON 3 kriFilter | JSON 2 kriDetails | kriId, kriName | Filter options |

---

## Implementation Notes

1. **Numeric Parsing**: Remove commas from numbers (e.g., "7,98,606.00" → 798606)
2. **Text Cleaning**: Remove line breaks from Control Procedures for validationDesc
3. **Null Handling**: Use `null` for controlDraftNumber when source is "null.1"
4. **Empty String vs Null**: Use "" for empty threshold fields, `null` for calculated fields
5. **Fund Order**: Process funds in the order they appear in Funds tab
6. **KRI Grouping**: Group by validation name before creating JSON 2
