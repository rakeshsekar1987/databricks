# Excel to JSON Relationship Analysis - Version 2

## Overview

This document analyzes the complete relationship mapping between input Excel data and output JSON files based on the updated requirements.

---

## Input Data Summary

### Cards Tab (1 record)
| Card Name | fiscal_year_end | reporting_cycle | open_end_close_end | reporting_date | Status |
|-----------|-----------------|-----------------|--------------------|--------------------|--------|
| 12/31/2024 Canada Annual | 31-Dec | Annual | Canada | 12/31/2024 | In-Cycle |

### Funds Tab (3 records)
| # | Trust | Trust_New | Fund ID_New | Group_New | Book_New | Fund Type |
|---|-------|-----------|-------------|-----------|----------|-----------|
| 23 | Canada | Canada | CAN1 | A | Income Strategy Fund | Canada |
| 24 | Canada | Canada | CAN2 | A | Credit Income Fund | Canada |
| 25 | Canada | Canada | CAN3 | A | International Bond Trust | Canada |

### Validations - TRIMMED (1 record)
| Fund | Validation | Priority | Status | BPS Impact |
|------|------------|----------|--------|------------|
| CAN3 | SCF_admin vs generalledger... | Material | Failed | -0.078014184 |

### Validations - KRI (3 records)
| Fund | Validation | Priority | Status | BPS Impact |
|------|------------|----------|--------|------------|
| CAN2 | Interest Expense versus Average Borrowings | Standard | Passed | 1.53 |
| CAN2 | Defaulted Securities Review | Standard | Passed | 0 |
| CAN3 | Effective Leverage: Year Over Year Change | Standard | Passed | 116.87 |

---

## Output File Naming Convention

### Pattern
Card Name is transformed to create file names:
- Input: `12/31/2024 Canada Annual`
- Output: `2024-12-31CanadaAnnual`

### Transformation Rules
1. Extract date parts: `12/31/2024` → `2024-12-31` (ISO format)
2. Remove date from Card Name, keep remaining text
3. Remove spaces and special characters
4. Concatenate: `{YYYY-MM-DD}{CardNameClean}`

### File Names for Each JSON
| JSON | File Name Pattern |
|------|-------------------|
| JSON 1 | `2024-12-31CanadaAnnual.json` |
| JSON 2 | `2024-12-31CanadaAnnualkri.json` |
| JSON 3 | `2024-12-31CanadaAnnualkri-fund.json` |
| JSON 4 | `2024-12-31CanadaAnnualstrategy.json` |
| JSON 5 | `2024-12-31CanadaAnnual.json` (same as JSON 1 or separate?) |

---

## KRI Master Data (Business-Provided)

Based on the expected output, the KRI Master must contain:

| KRI Name | KRI ID | Validation ID | Risk | Threshold |
|----------|--------|---------------|------|-----------|
| Interest Expense versus Average Borrowings | KRI_1 | 999991 | High | `{"High": ">7%","Medium": ">=7% and <=5%","Low":"<5%"}` |
| Defaulted Securities Review | KRI_6 | 999996 | Medium | `{"High": ">5%","Medium": ">=3% and <=5%","Low":"<3%"}` |
| Effective Leverage: Year Over Year Change | KRI_55 | 999999 | Low | `{"High": ">10%","Medium": ">=5% and <=10%","Low":"<5%"}` |

### Key Observations
1. **KRI IDs are NOT sequential** - They are business-defined (KRI_1, KRI_6, KRI_55)
2. **Risk is business-provided, NOT calculated from BPS**:
   - BPS 1.53 → "High" (for Interest Expense)
   - BPS 0 → "Medium" (for Defaulted Securities)
   - BPS 116.87 → "Low" (for Effective Leverage) - Note: High BPS maps to Low risk!
3. **Threshold is unique per KRI** - Different thresholds for each KRI
4. **Validation IDs** are pre-defined: 999991, 999996, 999999

---

## JSON 1: Combined Validations

### Field Mapping

| JSON Field | Source | Notes |
|------------|--------|-------|
| id | Generated | Unique hash (e.g., "9s5fd44acd...") |
| trust | Funds.Trust_New | Cross-reference via Fund |
| fund | Validations.Fund | Direct (CAN2, CAN3) |
| fundCode | Validations.Fund | Same as fund |
| group | Funds.Group_New | All are "A" in this data |
| book | Funds.Book_New | Cross-reference via Fund |
| shareClass | Validations.Share Class | Empty string |
| section | Validations.Section | For TRIMMED, for KRI empty |
| validation | Validations.Validation | Direct |
| controlValue | Validations.Control Value | Numeric |
| fsValue | Validations.FS Value | Numeric (parse commas: "7,98,606.00" → 798606) |
| variance | Validations.Variance | Numeric |
| bpsImpact | Validations.BPS Impact | Numeric |
| validationType | Validations.Validation Type | "AFS - Indicative FS" or "KRI Validations" |
| validationSource | Validations.Validation Source | "Recon_Engine" or "KRI Validations" |
| controlDraftNumber | Validations.Control Draft Number | For TRIMMED: extract integer (2.1→"2"), for KRI: null |
| autoManual | Validations.Auto / Manual | "Automated" |
| priority | Validations.Priority | "Material" or "Standard" |
| validationStatus | Validations.Validation Status | "Failed" or "Passed" |
| auditVersionControlDs | Default | Always "1" |
| writeTs | Generated | Timestamp (e.g., "2024-05-30 11:26:17.5450000") |
| isFinalDraft | Validations.Is Final | Boolean (false) |
| validationId | KRI Master or Generated | TRIMMED: "1161", KRI: from KRI Master |
| lineItemDescription | Validations.Line Item Description | For TRIMMED, for KRI empty |
| statementType | Validations.Statement Type | "SCF" or "KRI" |
| testDraftNumber | Validations.Test Draft Number | Usually empty |
| isCpoControl | Default | "0" |
| isCpoTest | Default | "0" |
| isBannerLessControl | Default | "0" |
| isBannerLessTest | Default | "0" |
| isBlueFontControl | Default | "0" |
| isBlueFontTest | Default | "0" |
| thresholdColAmount | Validations.Threshold Amount | Usually empty |
| thresholdColDesc | Validations.Threshold Desc | Usually empty |
| thresholdPercent | Validations.Threshold Percent (%) | Usually empty |
| thresholdAbs | Validations.Threshold Abs | Usually empty |
| validationDesc | Validations.Control Procedures | For KRI: cleaned multiline text |
| webappWorkflowStatus | Validations.Workflow Status | "EY L1 Review" |
| valuesUsedInFormula | KRI Variables | For KRI: JSON object, for TRIMMED: empty |
| analyticStatus | Default | null |
| fundStrategy | Default | null |
| result | Default | null |
| threshold | Default | null |

### Normal Validation (TRIMMED) validationId
The validationId for normal validations is "1161" - this appears to be a business-provided ID, not sequential from 1000.

---

## JSON 2: KRI Details

### Structure
```json
{
  "requestDetails": { "requestId": "..." },
  "data": {
    "kriDetails": [
      {
        "kriName": "...",
        "kriId": "KRI_X",
        "kriDesc": "...",
        "threshold": "{...}",
        "fundDetails": [...]
      }
    ]
  }
}
```

### Field Mapping

| JSON Field | Source | Notes |
|------------|--------|-------|
| kriName | Validations-KRI.Validation | Direct |
| kriId | KRI Master.KRI ID | Business-provided (KRI_1, KRI_6, KRI_55) |
| kriDesc | Validations-KRI.Control Procedures | Cleaned multiline text |
| threshold | KRI Master.Threshold | Business-provided JSON per KRI |
| fundDetails[].risk | KRI Master.Risk | Business-provided (NOT calculated) |
| fundDetails[].threshold | Default | Always null |
| fundDetails[].fundName | Funds.Book_New | Cross-reference |
| fundDetails[].fundCode | Validations-KRI.Fund | Direct |
| fundDetails[].result | Validations-KRI.BPS Impact | As string |
| fundDetails[].strategy | Default | "Credit - Diversified Income" |
| fundDetails[].validationStatus | Validations-KRI.Validation Status | Direct |
| fundDetails[].validationId | KRI Master.Validation ID | Business-provided |
| fundDetails[].valuesUsedInFormula | KRI Variables | JSON object |

---

## JSON 3: Fund KRI Status Count

### Structure
```json
{
  "requestDetails": { "requestId": "..." },
  "data": {
    "fundKriStatusCount": [...],
    "kriFilter": [...],
    "statusFilter": [...]
  }
}
```

### Field Mapping - fundKriStatusCount

| JSON Field | Source | Notes |
|------------|--------|-------|
| fundCode | Funds.Fund ID_New | All funds from Funds tab |
| fundName | Funds.Book_New | Cross-reference |
| kriTotalCount | Calculated | COUNT(DISTINCT KRI names) = "3" |
| kriStatusCount | Calculated | COUNT(KRI WHERE Fund = fundCode) |
| analyticsStatus | Default | "High" |

### Calculated Values
- CAN1: kriStatusCount = 0 (no KRI validations for this fund)
- CAN2: kriStatusCount = 2 (Interest Expense + Defaulted Securities)
- CAN3: kriStatusCount = 1 (Effective Leverage)

### kriFilter
List of all distinct KRIs with their IDs and validation IDs from KRI Master.

### statusFilter
Default: ["Low", "N/A", "High"]

---

## JSON 4: Strategy KRI Count

### Structure
```json
{
  "requestDetails": { "requestId": "..." },
  "data": [
    {
      "kriTotalCount": "3",
      "kriStatusCount": "3",
      "analyticsStatus": "High",
      "strategy": "Credit - Diversified Income"
    }
  ]
}
```

### Field Mapping
| JSON Field | Source | Notes |
|------------|--------|-------|
| kriTotalCount | Calculated | COUNT(DISTINCT KRI names) = "3" |
| kriStatusCount | Calculated | COUNT(ALL KRI validations) = "3" |
| analyticsStatus | Default | "High" |
| strategy | Default | "Credit - Diversified Income" |

---

## JSON 5: KRI Simple Details

### Structure
```json
{
  "kriDetails": [
    {
      "kriId": "KRI_X",
      "kriName": "...",
      "validationId": "..."
    }
  ]
}
```

### Field Mapping
Same as kriFilter in JSON 3 - list of distinct KRIs with IDs from KRI Master.

---

## Key Relationship Diagrams

### Cross-Reference: Validations → Funds

```
Validations.Fund  ──────────────────►  Funds.Fund ID_New
                                              │
                                              ├── Trust_New    → trust
                                              ├── Book_New     → book, fundName
                                              └── Group_New    → group
```

### Cross-Reference: Validations-KRI → KRI Master

```
Validations-KRI.Validation  ────────►  KRI Master.KRI Name
                                              │
                                              ├── KRI ID        → kriId
                                              ├── Validation ID → validationId
                                              ├── Threshold     → threshold (JSON)
                                              └── Risk          → risk (business-provided)
```

---

## Business-Provided Values Summary

The following values MUST come from business data (KRI Master), NOT be calculated:

| Field | Source | Example Values |
|-------|--------|----------------|
| KRI ID | KRI Master.KRI ID | KRI_1, KRI_6, KRI_55 (not sequential) |
| Validation ID | KRI Master.Validation ID | 999991, 999996, 999999 |
| Risk | KRI Master.Risk | High, Medium, Low (NOT from BPS) |
| Threshold | KRI Master.Threshold | Unique JSON per KRI |
| Group | Funds.Group_New | A (direct from column) |

---

## Default Values

| Field | Default Value | Notes |
|-------|---------------|-------|
| auditVersionControlDs | "1" | Always |
| isCpoControl | "0" | Always |
| isCpoTest | "0" | Always |
| isBannerLessControl | "0" | Always |
| isBannerLessTest | "0" | Always |
| isBlueFontControl | "0" | Always |
| isBlueFontTest | "0" | Always |
| analyticStatus (JSON1) | null | Always |
| fundStrategy (JSON1) | null | Always |
| result (JSON1) | null | Always |
| threshold (JSON1) | null | Always |
| analyticsStatus (JSON3/4) | "High" | Default for all |
| strategy (JSON2/4) | "Credit - Diversified Income" | Default |
| statusFilter | ["Low", "N/A", "High"] | Default array |

---

## Data Parsing Rules

### Number Parsing
- Indian comma format: "7,98,606.00" → 798606.0
- Negative numbers: -141, -25.06
- Decimal handling: 1.53, 116.87, -0.078014184

### Text Cleaning
- Remove newlines from Control Procedures
- Trim whitespace
- Preserve special characters

### Draft Number Extraction
- "2.1" → "2" (extract integer before decimal for controlDraftNumber)
- "null.1" → null (for KRI validations)

### valuesUsedInFormula
Build JSON object from KRI Variable Key/Value pairs:
```json
{
  "Average Borrowings": -36711,
  "Weighted Average Interest Rate": 4.38,
  "Interest Expense": -1633
}
```

---

## Validation Rules

1. Every Fund in Validations must exist in Funds tab
2. Every KRI validation must have matching KRI Master entry
3. kriTotalCount must equal distinct KRI count
4. kriStatusCount per fund must equal actual KRI count for that fund
5. All IDs must be consistent across JSON files
