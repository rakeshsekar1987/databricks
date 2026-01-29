# Detailed Field-by-Field Analysis

## Input Data Review

### Cards Tab (1 record)
```
Card Name           | 12/31/2024 Canada Annual
fiscal_year_end     | 31-Dec
reporting_cycle     | Annual
open_end_close_end  | Canada
reporting_date      | 31-12-2024
Status              | In-Cycle
```

### Funds Tab (3 records)

| # | Trust | Trust_New | Fund | Fund ID | Fund Name_New | Fund ID_New | Group | Group_New | Book | Book_New | Fund Type |
|---|-------|-----------|------|---------|---------------|-------------|-------|-----------|------|----------|-----------|
| 23 | Canada | Canada | PIMCO Monthly Income Fund (Canada) | HD2C | Income Strategy Fund | CAN1 | H | A | PIMCO Monthly Income Fund (Canada) | Income Strategy Fund | Canada |
| 24 | Canada | Canada | PIMCO Monthly Enhanced Income Fund | HEWM | Credit Income Fund | CAN2 | H | A | Canada CEF | Credit Income Fund | Canada |
| 25 | Canada | Canada | PIMCO Canada Canadian CorePLUS Bond Trust | HDW1 | International Bond Trust | CAN3 | G | A | Canada Trust | International Bond Trust | Canada |

### Validations - TRIMMED Tab (1 record)

| Field | Value |
|-------|-------|
| Card | 12/31/2024 Canada Annual |
| Fund | CAN3 |
| Priority | Material |
| Workflow Status | EY L1 Review |
| Validation Status | Failed |
| Validation | SCF_admin vs generalledger_adjusted_entries_ey_CANADA |
| Statement Type | SCF |
| Section | Net Realized (Gain) Loss |
| Line Item Description | Foreign currency transactions |
| Control Procedures | SCF_admin vs generalledger_adjusted_entries_ey_CANADA |
| Share Class | (empty) |
| Control Value | -141 |
| FS Value | -152 |
| Variance | 11 |
| BPS Impact | -0.078014184 |
| Auto / Manual | Automated |
| Validation Source | Recon_Engine |
| Validation Type | AFS - Indicative FS |
| Control Draft Number | 2.1 |
| Test Draft Number | (empty) |
| Is Final | (empty) |
| Threshold Desc | -- |
| Threshold Percent (%) | -- |

### Validations - KRI Tab (3 records)

**Record 1:**
| Field | Value |
|-------|-------|
| Card | 12/31/2024 Canada Annual |
| Fund | CAN2 |
| Priority | Standard |
| Workflow Status | EY L1 Review |
| Validation Status | Passed |
| Validation | Interest Expense versus Average Borrowings |
| Statement Type | KRI |
| Section | (empty) |
| Line Item Description | (empty) |
| Control Procedures | Percent difference between the Interest Expense versus the Average Borrowings... |
| Control Value | -25.06 |
| FS Value | -1633 |
| Variance | -25.06 |
| BPS Impact | 1.53 |
| Auto / Manual | Automated |
| Validation Source | KRI Validations |
| Validation Type | KRI Validations |
| Control Draft Number | null.1 |
| KRI Variable Key1 | Average Borrowings |
| KRI Variable Value1 | -36711 |
| KRI Variable Key2 | Weighted Average Interest Rate |
| KRI Variable Value2 | 4.38 |
| KRI Variable Key3 | Interest Expense |
| KRI Variable Value3 | -1633 |

**Record 2:**
| Field | Value |
|-------|-------|
| Card | 12/31/2024 Canada Annual |
| Fund | CAN2 |
| Priority | Standard |
| Workflow Status | EY L1 Review |
| Validation Status | Passed |
| Validation | Defaulted Securities Review |
| Statement Type | KRI |
| Control Procedures | Total Market Value of Securities in Default as a percentage of Net Assets... |
| Control Value | 0 |
| FS Value | 7,98,606.00 |
| Variance | 0 |
| BPS Impact | 0 |
| Auto / Manual | Automated |
| Validation Source | KRI Validations |
| Validation Type | KRI Validations |
| Control Draft Number | null.1 |
| KRI Variable Key1 | Total Market Value Of Securities In Default |
| KRI Variable Value1 | 0 |
| KRI Variable Key2 | Net Assets |
| KRI Variable Value2 | 7,98,606.00 |

**Record 3:**
| Field | Value |
|-------|-------|
| Card | 12/31/2024 Canada Annual |
| Fund | CAN3 |
| Priority | Standard |
| Workflow Status | EY L1 Review |
| Validation Status | Passed |
| Validation | Effective Leverage: Year Over Year Change |
| Statement Type | KRI |
| Control Procedures | Period over period change for a Fund's Total Effective Leverage... |
| Control Value | 0.02 |
| FS Value | 0.02 |
| Variance | 0 |
| BPS Impact | 116.87 |
| Auto / Manual | Automated |
| Validation Source | KRI Validations |
| Validation Type | KRI Validations |
| Control Draft Number | null.1 |
| KRI Variable Key1 | Py Net Assets |
| KRI Variable Value1 | 18,17,515.00 |
| KRI Variable Key2 | Cy Reverse Repos |
| KRI Variable Value2 | 9,500.00 |
| KRI Variable Key3 | Cy Credit Default Swaps |
| KRI Variable Value3 | 51,800.00 |
| KRI Variable Key4 | Cy Net Assets |
| KRI Variable Value4 | 17,14,756.00 |
| KRI Variable Key5 | Cy Line Of Credit |
| KRI Variable Value5 | 0 |

---

## JSON 1: Line-by-Line Field Mapping

### Validation 1 (TRIMMED - CAN3)

| JSON Field | Expected Value | Source | Derivation |
|------------|----------------|--------|------------|
| id | 9s5fd44acd...75be | Generated | Hash based on content |
| trust | Canada | Funds.Trust_New | Lookup: CAN3 → Trust_New = "Canada" |
| fund | CAN3 | Validations.Fund | Direct: "CAN3" |
| shareClass | "" | Validations.Share Class | Direct: (empty) |
| section | Net Realized (Gain) Loss | Validations.Section | Direct |
| validation | SCF_admin vs generalledger... | Validations.Validation | Direct |
| controlValue | -141 | Validations.Control Value | Parse as number |
| fsValue | -152 | Validations.FS Value | Parse as number |
| variance | 11 | Validations.Variance | Parse as number |
| bpsImpact | -0.078014184 | Validations.BPS Impact | Parse as number |
| validationType | AFS - Indicative FS | Validations.Validation Type | Direct |
| validationSource | Recon_Engine | Validations.Validation Source | Direct |
| controlDraftNumber | "2" | Validations.Control Draft Number | Extract integer from "2.1" |
| autoManual | Automated | Validations.Auto / Manual | Direct |
| fundCode | CAN3 | Validations.Fund | Same as fund |
| **group** | **C** | **Derived** | **CAN3 → extract "3" → letter "C"** |
| book | International Bond Trust | Funds.Book_New | Lookup: CAN3 → Book_New |
| priority | Material | Validations.Priority | Direct |
| validationStatus | Failed | Validations.Validation Status | Direct |
| auditVersionControlDs | "1" | Default | Always "1" |
| writeTs | 2024-05-30 11:26:17... | Generated | Timestamp |
| isFinalDraft | false | Validations.Is Final | Parse as boolean |
| validationId | "1161" | Generated | Sequential for non-KRI |
| lineItemDescription | Foreign currency transactions | Validations.Line Item Description | Direct |
| statementType | SCF | Validations.Statement Type | Direct |
| testDraftNumber | "" | Validations.Test Draft Number | Direct |
| thresholdColAmount | "" | Validations.Threshold Amount | Direct |
| thresholdColDesc | "--" | Validations.Threshold Desc | Direct |
| thresholdPercent | "--" | Validations.Threshold Percent (%) | Direct |
| thresholdAbs | "" | Validations.Threshold Abs | Direct |
| validationDesc | SCF_admin vs generalledger... | Validations.Validation | For non-KRI: use Validation field |
| webappWorkflowStatus | EY L1 Review | Validations.Workflow Status | Direct |
| valuesUsedInFormula | "" | N/A | Empty for non-KRI |

### Validation 2 (KRI - CAN2 - Interest Expense)

| JSON Field | Expected Value | Source | Derivation |
|------------|----------------|--------|------------|
| id | 0t5fd44acd...75be | Generated | Hash |
| trust | Canada | Funds.Trust_New | Lookup: CAN2 → "Canada" |
| fund | CAN2 | Validations.Fund | Direct |
| shareClass | "" | Validations.Share Class | Direct |
| section | "" | Validations.Section | Direct (empty) |
| validation | Interest Expense versus Average Borrowings | Validations.Validation | Direct |
| controlValue | -25.06 | Validations.Control Value | Direct |
| fsValue | -1633 | Validations.FS Value | Parse as number |
| variance | -25.06 | Validations.Variance | Direct |
| bpsImpact | 1.53 | Validations.BPS Impact | Direct |
| validationType | KRI Validations | Validations.Validation Type | Direct |
| validationSource | KRI Validations | Validations.Validation Source | Direct |
| controlDraftNumber | null | Validations.Control Draft Number | "null.1" → null |
| autoManual | Automated | Validations.Auto / Manual | Direct |
| fundCode | CAN2 | Validations.Fund | Same as fund |
| **group** | **B** | **Derived** | **CAN2 → extract "2" → letter "B"** |
| book | Credit Income Fund | Funds.Book_New | Lookup: CAN2 → Book_New |
| priority | Standard | Validations.Priority | Direct |
| validationStatus | Passed | Validations.Validation Status | Direct |
| validationId | "999991" | KRI Master | KRI_1 → 999991 |
| lineItemDescription | "" | Validations.Line Item Description | Direct |
| statementType | KRI | Validations.Statement Type | Direct |
| validationDesc | Percent difference between... | Validations.Control Procedures | For KRI: use Control Procedures |
| webappWorkflowStatus | EY L1 Review | Validations.Workflow Status | Direct |
| valuesUsedInFormula | {"Average Borrowings": -36711, ...} | KRI Variables | Build from Key1-5 + Value1-5 |

### Validation 3 (KRI - CAN2 - Defaulted Securities)

| JSON Field | Expected Value | Source | Derivation |
|------------|----------------|--------|------------|
| fund | CAN2 | Validations.Fund | Direct |
| **group** | **B** | **Derived** | **CAN2 → "2" → "B"** |
| book | Credit Income Fund | Funds.Book_New | Lookup |
| validationId | "999996" | KRI Master | KRI_6 → 999996 |
| fsValue | 798606 | Validations.FS Value | "7,98,606.00" → 798606 (remove commas) |
| valuesUsedInFormula | {"Total Market Value...": 0, "Net Assets": 798606} | KRI Variables | Build from Key/Value pairs |

### Validation 4 (KRI - CAN3 - Effective Leverage)

| JSON Field | Expected Value | Source | Derivation |
|------------|----------------|--------|------------|
| fund | CAN3 | Validations.Fund | Direct |
| **group** | **C** | **Derived** | **CAN3 → "3" → "C"** |
| book | International Bond Trust | Funds.Book_New | Lookup |
| validationId | "999999" | KRI Master | KRI_9A → 999999 |
| priority | Standard | Validations.Priority | Direct (Excel says Standard) |
| bpsImpact | 116.87 | Validations.BPS Impact | Direct |
| valuesUsedInFormula | {"Py Net Assets": 1817515, ...} | KRI Variables | Build from Key/Value pairs |

---

## Key Finding: Group Derivation

**The `group` field is NOT from Funds.Group or Funds.Group_New!**

| Fund ID_New | Funds.Group | Funds.Group_New | Expected JSON group | Derivation |
|-------------|-------------|-----------------|---------------------|------------|
| CAN1 | H | A | A | CAN**1** → 1 → A |
| CAN2 | H | A | B | CAN**2** → 2 → B |
| CAN3 | G | A | C | CAN**3** → 3 → C |

**Rule:** Extract numeric suffix from Fund ID_New, convert to letter (1→A, 2→B, 3→C, etc.)

---

## JSON 2: KRI Details Field Mapping

### KRI Group 1: Interest Expense versus Average Borrowings

| JSON Field | Expected Value | Source | Derivation |
|------------|----------------|--------|------------|
| kriName | Interest Expense versus Average Borrowings | Validations-KRI.Validation | Direct |
| kriId | KRI_1 | KRI Master | Lookup by kriName |
| kriDesc | Percent difference between... | Validations-KRI.Control Procedures | Clean text |
| threshold | {"High": ">30%",...} | KRI Master or Default | Default threshold |
| fundDetails[0].risk | Low | Calculated | BPS 1.53 < 15 → "Low" |
| fundDetails[0].fundName | Credit Income Fund | Funds.Book_New | Lookup: CAN2 → Book_New |
| fundDetails[0].fundCode | CAN2 | Validations-KRI.Fund | Direct |
| fundDetails[0].result | "1.53" | Validations-KRI.BPS Impact | As string |
| fundDetails[0].validationStatus | Passed | Validations-KRI.Validation Status | Direct |
| fundDetails[0].validationId | "999991" | KRI Master | Same as JSON 1 |
| fundDetails[0].valuesUsedInFormula | {"Average Borrowings": -36711, ...} | KRI Variables | Build from Key/Value |

### KRI Group 2: Defaulted Securities Review

| JSON Field | Expected Value | Source |
|------------|----------------|--------|
| kriId | KRI_6 | KRI Master |
| fundDetails[0].risk | Low | BPS 0 < 15 → "Low" |
| fundDetails[0].fundName | Credit Income Fund | Funds.Book_New for CAN2 |
| fundDetails[0].result | "0.0" or "0" | BPS Impact as string |
| fundDetails[0].validationId | "999996" | KRI Master (KRI_6) |

### KRI Group 3: Effective Leverage

| JSON Field | Expected Value | Source |
|------------|----------------|--------|
| kriId | KRI_9A | KRI Master |
| fundDetails[0].risk | High | BPS 116.87 ≥ 30 → "High" |
| fundDetails[0].fundName | International Bond Trust | Funds.Book_New for CAN3 |
| fundDetails[0].result | "116.87" | BPS Impact as string |
| fundDetails[0].validationId | "999999" | KRI Master (KRI_9A) |

---

## JSON 3: Fund KRI Status Count Field Mapping

### fundKriStatusCount Array

| fundCode | fundName Source | kriTotalCount | kriStatusCount Source |
|----------|-----------------|---------------|----------------------|
| CAN1 | Funds.Fund Name_New | 3 (count of distinct KRI names) | 0 (no KRI records for CAN1) |
| CAN2 | Funds.Fund Name_New | 3 | 2 (Interest Expense + Defaulted Securities) |
| CAN3 | Funds.Fund Name_New | 3 | 1 (Effective Leverage) |

**Note:** In JSON 3, `fundName` comes from `Fund Name_New`, not `Book_New`!

| Fund ID_New | Fund Name_New | Book_New | Same? |
|-------------|---------------|----------|-------|
| CAN1 | Income Strategy Fund | Income Strategy Fund | Yes |
| CAN2 | Credit Income Fund | Credit Income Fund | Yes |
| CAN3 | International Bond Trust | International Bond Trust | Yes |

In this dataset they're the same, but semantically:
- JSON 2 fundDetails.fundName = Book_New (investment book name)
- JSON 3 fundKriStatusCount.fundName = Fund Name_New (fund display name)

---

## JSON 4: Strategy KRI Count

| Field | Value | Derivation |
|-------|-------|------------|
| kriTotalCount | "3" | COUNT(DISTINCT KRI names) = 3 |
| kriStatusCount | "3" | COUNT(all KRI validations) = 3 |
| analyticsStatus | "High" | Default |
| strategy | "Credit - Diversified Income" | Default (could be from Funds if column exists) |

---

## JSON 5: KRI Simple Details

| kriId | kriName | validationId |
|-------|---------|--------------|
| KRI_1 | Interest Expense versus Average Borrowings | 999991 |
| KRI_6 | Defaulted Securities Review | 999996 |
| KRI_9A | Effective Leverage: Year Over Year Change | 999999 |

---

## KRI ID to Validation ID Mapping

| KRI Name | kriId (from KRI Master) | validationId | Pattern |
|----------|-------------------------|--------------|---------|
| Interest Expense versus Average Borrowings | KRI_1 | 999991 | 999990 + 1 |
| Defaulted Securities Review | KRI_6 | 999996 | 999990 + 6 |
| Effective Leverage: Year Over Year Change | KRI_9A | 999999 | 999990 + 9 |

**Pattern:** validationId = 999990 + (numeric part of kriId)

---

## Number Parsing Rules

| Original Value | Parsed Value | Rule |
|----------------|--------------|------|
| -141 | -141.0 | Direct |
| 7,98,606.00 | 798606.0 | Remove all commas |
| 18,17,515.00 | 1817515.0 | Remove all commas |
| 9,500.00 | 9500.0 | Remove all commas |
| 0.02 | 0.02 | Direct |
| 4.38 | 4.38 | Direct |

---

## Control Draft Number Parsing

| Original Value | Parsed Value | Rule |
|----------------|--------------|------|
| 2.1 | "2" | Extract integer part |
| null.1 | null | "null.1" or "null" → null |
| (empty) | "" | Empty string |

---

## Summary of Cross-References

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Validations.Fund = "CAN2"                                                   │
│         │                                                                   │
│         ├──────────────────────────────────────────────────────────────────┤
│         │                     LOOKUP IN FUNDS TAB                           │
│         │                                                                   │
│         ▼                                                                   │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Find row where Fund ID_New = "CAN2"                                      ││
│ │                                                                          ││
│ │ Returns:                                                                 ││
│ │   Trust_New = "Canada"              → JSON trust                         ││
│ │   Book_New = "Credit Income Fund"   → JSON book, fundName (JSON 2)       ││
│ │   Fund Name_New = "Credit Income Fund" → fundName (JSON 3)               ││
│ │   Fund ID_New = "CAN2"              → Derive group: "2" → "B"            ││
│ └─────────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Discrepancy Found

In the expected JSON 1 output, the 4th validation shows:
```json
"priority": "Material"
```

But in the Excel KRI data, this record has:
```
Priority: Standard
```

**This is a discrepancy.** Either:
1. The expected output has a typo
2. There's a business rule overriding priority (e.g., BPS > 100 → Material)

**Current implementation:** Uses Priority value directly from Excel (data-driven approach).
