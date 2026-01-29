# Excel to JSON Data Relationship Diagram

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXCEL INPUT                                     │
│                           (4 Tabs/Sheets)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐         ┌─────────────────┐         ┌─────────────────┐
│    CARDS      │         │     FUNDS       │         │  VALIDATIONS    │
│    Tab        │         │      Tab        │         │   (2 Tabs)      │
├───────────────┤         ├─────────────────┤         ├─────────────────┤
│• Card Name    │         │• Fund ID_New    │         │• TRIMMED Tab    │
│• fiscal_year  │         │• Trust_New      │         │• KRI Tab        │
│• reporting_   │         │• Fund Name_New  │         │                 │
│  cycle        │         │• Group_New      │         │ Both have:      │
│• Status       │         │• Book_New       │         │• Card (FK)      │
│               │         │• Fund Type      │         │• Fund (FK)      │
└───────────────┘         └─────────────────┘         └─────────────────┘
        │                         │                           │
        │     ┌───────────────────┘                           │
        │     │                                               │
        ▼     ▼                                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CROSS-REFERENCE LAYER                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  FOREIGN KEY RELATIONSHIPS:                                          │    │
│  │                                                                       │    │
│  │  Validations.Card ───────────────────────▶ Cards.Card Name           │    │
│  │           │                                                           │    │
│  │           │  (Used for context, reporting period)                     │    │
│  │                                                                       │    │
│  │  Validations.Fund ───────────────────────▶ Funds.Fund ID_New         │    │
│  │           │                                                           │    │
│  │           │  (Used to lookup: trust, group, book, fundName)          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  MERGE OPERATION:                                                     │    │
│  │                                                                       │    │
│  │  Validations-TRIMMED ─────┐                                          │    │
│  │                           ├──────▶ Combined Validations List          │    │
│  │  Validations-KRI ─────────┘                                          │    │
│  │                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRANSFORMATION LAYER                                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  AUTO-GENERATED FIELDS:                                               │    │
│  │  • id (unique hash)           • validationId (sequential/mapped)      │    │
│  │  • requestId (UUID)           • auditVersionControlDs ("1")           │    │
│  │  • writeTs (timestamp)        • rowCount (calculated)                 │    │
│  │  • kriId (mapped from name)   • kriStatusCount (aggregated)           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  FIELD MAPPINGS:                                                      │    │
│  │                                                                       │    │
│  │  Group Mapping:    Fund → Group Letter (CAN1→A, CAN2→B, CAN3→C)       │    │
│  │  KRI ID Mapping:   Validation Name → KRI_ID (KRI_1, KRI_6, KRI_9A)   │    │
│  │  Values Formula:   KRI Variables 1-5 → JSON string                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  AGGREGATIONS:                                                        │    │
│  │                                                                       │    │
│  │  JSON 3: GROUP BY fund → COUNT(kri_validations)                       │    │
│  │  JSON 4: SUM ALL → total kri count per strategy                       │    │
│  │  JSON 2: GROUP BY kri_name → list of fund details                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────┬───────────┬───┴───────┬───────────┐
        │           │           │           │           │
        ▼           ▼           ▼           ▼           ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│  JSON 1   │ │  JSON 2   │ │  JSON 3   │ │  JSON 4   │ │  JSON 5   │
│ Combined  │ │   KRI     │ │ Fund KRI  │ │ Strategy  │ │   KRI     │
│Validations│ │  Details  │ │  Status   │ │   Count   │ │  Simple   │
└───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘
```

## Detailed Field Relationships

### JSON 1: Combined Validations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JSON 1 FIELD SOURCES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  DIRECT MAPPINGS (from Validations tab):                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ fund ◄──────────────── Validations.Fund                                 │ │
│  │ validation ◄────────── Validations.Validation                           │ │
│  │ controlValue ◄──────── Validations.Control Value                        │ │
│  │ fsValue ◄───────────── Validations.FS Value (with comma removal)        │ │
│  │ variance ◄──────────── Validations.Variance                             │ │
│  │ bpsImpact ◄─────────── Validations.BPS Impact                           │ │
│  │ priority ◄──────────── Validations.Priority                             │ │
│  │ validationStatus ◄──── Validations.Validation Status                    │ │
│  │ statementType ◄─────── Validations.Statement Type                       │ │
│  │ section ◄───────────── Validations.Section                              │ │
│  │ lineItemDescription ◄─ Validations.Line Item Description                │ │
│  │ autoManual ◄────────── Validations.Auto / Manual                        │ │
│  │ validationSource ◄──── Validations.Validation Source                    │ │
│  │ validationType ◄────── Validations.Validation Type                      │ │
│  │ webappWorkflowStatus ◄ Validations.Workflow Status                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  CROSS-REFERENCED (from Funds tab via Fund lookup):                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ trust ◄─────────────── Funds.Trust_New                                  │ │
│  │ book ◄──────────────── Funds.Book_New                                   │ │
│  │ group ◄─────────────── MAPPED(Funds.Fund ID_New) → (A, B, C)            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  AUTO-GENERATED:                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ id ◄────────────────── Generated unique hash                            │ │
│  │ validationId ◄──────── Sequential number or KRI pattern                 │ │
│  │ auditVersionControlDs ◄ Always "1"                                      │ │
│  │ writeTs ◄───────────── Current timestamp                                │ │
│  │ requestId ◄─────────── Generated UUID                                   │ │
│  │ rowCount ◄──────────── COUNT(all validations)                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  KRI-SPECIFIC (only for KRI validations):                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ valuesUsedInFormula ◄─ JSON({                                           │ │
│  │                          KRI Variable Key1: KRI Variable Value1,        │ │
│  │                          KRI Variable Key2: KRI Variable Value2,        │ │
│  │                          ...                                            │ │
│  │                        })                                               │ │
│  │ validationDesc ◄────── Validations-KRI.Control Procedures               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  DEFAULT VALUES:                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ isCpoControl: "0"     isCpoTest: "0"                                    │ │
│  │ isBannerLessControl: "0"     isBannerLessTest: "0"                      │ │
│  │ isBlueFontControl: "0"       isBlueFontTest: "0"                        │ │
│  │ analyticStatus: null  fundStrategy: null                                │ │
│  │ result: null          threshold: null                                   │ │
│  │ hasNextPage: false    hasPreviousPage: false                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### JSON 2: KRI Details

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JSON 2 FIELD SOURCES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GROUPING LOGIC:                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                         │ │
│  │   Validations-KRI                                                       │ │
│  │         │                                                               │ │
│  │         │  GROUP BY Validation Name                                     │ │
│  │         ▼                                                               │ │
│  │   ┌─────────────────┐                                                   │ │
│  │   │ KRI Group 1     │──┬──▶ fundDetails[0] ──▶ Fund CAN2               │ │
│  │   │ (e.g. Interest  │  │                                                │ │
│  │   │  Expense...)    │  └──▶ fundDetails[1] ──▶ Fund CAN3 (if exists)   │ │
│  │   └─────────────────┘                                                   │ │
│  │                                                                         │ │
│  │   ┌─────────────────┐                                                   │ │
│  │   │ KRI Group 2     │──────▶ fundDetails[0] ──▶ Fund CAN2               │ │
│  │   │ (e.g. Defaulted │                                                   │ │
│  │   │  Securities)    │                                                   │ │
│  │   └─────────────────┘                                                   │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  FIELD MAPPINGS:                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ kriName ◄───────────── Validations-KRI.Validation                       │ │
│  │ kriId ◄─────────────── MAPPED(Validation Name) → KRI_1, KRI_6, etc.     │ │
│  │ kriDesc ◄───────────── Validations-KRI.Control Procedures (cleaned)     │ │
│  │ threshold ◄─────────── DEFAULT JSON with High/Medium/Low                │ │
│  │                                                                         │ │
│  │ fundDetails[].fundCode ◄─── Validations-KRI.Fund                        │ │
│  │ fundDetails[].fundName ◄─── Funds.Book_New (via Fund lookup)            │ │
│  │ fundDetails[].result ◄───── Validations-KRI.BPS Impact (as string)      │ │
│  │ fundDetails[].risk ◄─────── CALCULATED from BPS Impact                  │ │
│  │ fundDetails[].validationStatus ◄── Validations-KRI.Validation Status    │ │
│  │ fundDetails[].validationId ◄────── Same as JSON 1 validationId          │ │
│  │ fundDetails[].valuesUsedInFormula ◄ KRI Variables as JSON               │ │
│  │ fundDetails[].strategy ◄────────── DEFAULT: "Credit - Diversified..."   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### JSON 3: Fund KRI Status Count

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JSON 3 FIELD SOURCES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FUND KRI STATUS COUNT (for each fund in Funds tab):                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                         │ │
│  │   FOR each Fund in Funds tab:                                           │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │   │ fundCode ◄──────────── Funds.Fund ID_New                         │  │ │
│  │   │ fundName ◄──────────── Funds.Fund Name_New                       │  │ │
│  │   │ kriTotalCount ◄─────── COUNT(DISTINCT KRI validation names)      │  │ │
│  │   │ kriStatusCount ◄────── COUNT(KRI validations WHERE Fund = this)  │  │ │
│  │   │ analyticsStatus ◄───── DEFAULT: "High"                           │  │ │
│  │   └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  KRI FILTER (distinct KRI types):                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │   FOR each DISTINCT Validation Name in Validations-KRI:                 │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │   │ kriId ◄─────────────── MAPPED(Validation Name)                   │  │ │
│  │   │ kriName ◄───────────── Validations-KRI.Validation                │  │ │
│  │   │ validationId ◄──────── Same as JSON 1 validationId               │  │ │
│  │   └─────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  STATUS FILTER:                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ statusFilter ◄──────────── ["Low", "N/A", "High"] (static list)         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### JSON 4: Strategy KRI Count

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JSON 4 FIELD SOURCES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  AGGREGATION:                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                         │ │
│  │   kriTotalCount ◄───────── COUNT(DISTINCT KRI validation names)         │ │
│  │                                                                         │ │
│  │   kriStatusCount ◄──────── COUNT(ALL KRI validations)                   │ │
│  │                                                                         │ │
│  │   analyticsStatus ◄─────── DEFAULT: "High"                              │ │
│  │                                                                         │ │
│  │   strategy ◄────────────── DEFAULT: "Credit - Diversified Income"       │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### JSON 5: KRI Simple Details

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JSON 5 FIELD SOURCES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SIMPLE LIST (same as kriFilter in JSON 3):                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │   FOR each DISTINCT Validation Name in Validations-KRI:                 │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │   │ kriId ◄─────────────── MAPPED(Validation Name)                   │  │ │
│  │   │ kriName ◄───────────── Validations-KRI.Validation                │  │ │
│  │   │ validationId ◄──────── Same as JSON 1 validationId               │  │ │
│  │   └─────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Count Calculations Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COUNT CALCULATIONS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  rowCount (JSON 1):                                                          │
│  ═══════════════════                                                         │
│  COUNT(Validations-TRIMMED) + COUNT(Validations-KRI)                         │
│  = 1 + 3 = 4                                                                 │
│                                                                              │
│  kriTotalCount (JSON 3, 4):                                                  │
│  ═════════════════════════                                                   │
│  COUNT(DISTINCT Validation names in Validations-KRI)                         │
│  = 3 (Interest Expense, Defaulted Securities, Effective Leverage)            │
│                                                                              │
│  kriStatusCount per Fund (JSON 3):                                           │
│  ══════════════════════════════════                                          │
│  CAN1: COUNT(KRI WHERE Fund = CAN1) = 0                                      │
│  CAN2: COUNT(KRI WHERE Fund = CAN2) = 2                                      │
│  CAN3: COUNT(KRI WHERE Fund = CAN3) = 1                                      │
│                                                                              │
│  kriStatusCount Total (JSON 4):                                              │
│  ═══════════════════════════════                                             │
│  COUNT(ALL KRI validations) = 3                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## ID Consistency Across JSONs

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ID CONSISTENCY DIAGRAM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   The same validationId is used consistently across all JSONs:               │
│                                                                              │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐               │
│   │ JSON 1  │     │ JSON 2  │     │ JSON 3  │     │ JSON 5  │               │
│   │validat- │     │fundDet- │     │kriFilter│     │kriDet-  │               │
│   │ions[].  │ ════│ails[].  │ ════│[].valid-│ ════│ails[].  │               │
│   │validat- │     │validat- │     │ationId  │     │validat- │               │
│   │ionId    │     │ionId    │     │         │     │ionId    │               │
│   └─────────┘     └─────────┘     └─────────┘     └─────────┘               │
│        ║               ║               ║               ║                     │
│        ║               ║               ║               ║                     │
│        ╚═══════════════╩═══════════════╩═══════════════╝                     │
│                            │                                                 │
│                            ▼                                                 │
│                   ┌─────────────────┐                                        │
│                   │ SAME VALUE FOR  │                                        │
│                   │ SAME VALIDATION │                                        │
│                   │ e.g., "999991"  │                                        │
│                   └─────────────────┘                                        │
│                                                                              │
│   Similarly for kriId:                                                       │
│                                                                              │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐                               │
│   │ JSON 2  │     │ JSON 3  │     │ JSON 5  │                               │
│   │kriDet-  │ ════│kriFilter│ ════│kriDet-  │                               │
│   │ails[].  │     │[].kriId │     │ails[].  │                               │
│   │kriId    │     │         │     │kriId    │                               │
│   └─────────┘     └─────────┘     └─────────┘                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```
