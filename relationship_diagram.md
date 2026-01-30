# Excel to JSON Data Relationship Diagram - Data-Driven Version

## Core Principle: Everything Derived from Data

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     NO HARDCODED MAPPINGS                                    │
│                                                                              │
│  ✓ Group letters derived from Fund ID pattern (CAN1→A, CAN2→B)              │
│  ✓ KRI IDs from KRI Master tab or auto-generated sequentially               │
│  ✓ Validation IDs based on row order or KRI Master lookup                   │
│  ✓ All counts calculated from actual data                                   │
│  ✓ Cross-references built dynamically from loaded data                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXCEL INPUT                                     │
│                           (4+ Tabs/Sheets)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────┬───────────────────┼───────────────────┬───────────┐
    │           │                   │                   │           │
    ▼           ▼                   ▼                   ▼           ▼
┌────────┐ ┌─────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌──────────┐
│ Cards  │ │  Funds  │ │  Validations-   │ │  Validations-   │ │   KRI    │
│  Tab   │ │   Tab   │ │    TRIMMED      │ │      KRI        │ │  Master  │
│        │ │         │ │                 │ │                 │ │(Optional)│
└────┬───┘ └────┬────┘ └────────┬────────┘ └────────┬────────┘ └────┬─────┘
     │          │               │                   │               │
     │          │               │                   │               │
     ▼          ▼               ▼                   ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA LOOKUP SERVICE                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ INDEXES BUILT DYNAMICALLY FROM LOADED DATA:                             │ │
│  │                                                                         │ │
│  │ Fund Index:                                                             │ │
│  │ ┌─────────────────────────────────────────────────────────────────────┐│ │
│  │ │ Fund ID_New  →  { trust, book, fundName, derivedGroupLetter }       ││ │
│  │ │ CAN1         →  { Canada, Income Strategy Fund, A }                 ││ │
│  │ │ CAN2         →  { Canada, Credit Income Fund, B }                   ││ │
│  │ │ CAN3         →  { Canada, International Bond Trust, C }             ││ │
│  │ └─────────────────────────────────────────────────────────────────────┘│ │
│  │                                                                         │ │
│  │ KRI Index (from KRI Master or auto-generated):                          │ │
│  │ ┌─────────────────────────────────────────────────────────────────────┐│ │
│  │ │ KRI Name                                    →  kriId, validationId  ││ │
│  │ │ Interest Expense versus Average Borrowings  →  KRI_1, 999991        ││ │
│  │ │ Defaulted Securities Review                 →  KRI_6, 999996        ││ │
│  │ │ Effective Leverage: Year Over Year Change   →  KRI_9A, 999999       ││ │
│  │ └─────────────────────────────────────────────────────────────────────┘│ │
│  └────────────────────────────────────────────────────────────────────────┘ │
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

## Detailed Data Derivation Rules

### Rule 1: Group Letter Derivation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GROUP LETTER DERIVATION                                 │
│                                                                              │
│   INPUT: Funds.Fund ID_New                                                   │
│                                                                              │
│   RULE: Extract numeric suffix → Convert to letter (1=A, 2=B, 3=C, ...)     │
│                                                                              │
│   EXAMPLES:                                                                  │
│   ┌──────────────┬─────────────────┬────────────────┐                       │
│   │ Fund ID_New  │ Numeric Suffix  │ Output Group   │                       │
│   ├──────────────┼─────────────────┼────────────────┤                       │
│   │ CAN1         │ 1               │ A              │                       │
│   │ CAN2         │ 2               │ B              │                       │
│   │ CAN3         │ 3               │ C              │                       │
│   │ FUND10       │ 10              │ J              │                       │
│   │ ABC26        │ 26              │ Z              │                       │
│   └──────────────┴─────────────────┴────────────────┘                       │
│                                                                              │
│   CODE:                                                                      │
│   def get_group(fund_id_new):                                                │
│       match = re.match(r'^[A-Za-z]+(\d+)', fund_id_new)                     │
│       if match:                                                              │
│           number = int(match.group(1))                                       │
│           return chr(ord('A') + number - 1)                                  │
│       return 'A'  # fallback                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Rule 2: KRI ID and Validation ID

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KRI ID GENERATION                                         │
│                                                                              │
│   OPTION A: With KRI Master Tab (Recommended for Production)                 │
│   ─────────────────────────────────────────────────────────                  │
│                                                                              │
│   KRI Master Tab provides:                                                   │
│   ┌────────────────────────────────────────────┬─────────┬─────────────┐    │
│   │ KRI Name                                   │ KRI ID  │Validation ID│    │
│   ├────────────────────────────────────────────┼─────────┼─────────────┤    │
│   │ Interest Expense versus Average Borrowings │ KRI_1   │ 999991      │    │
│   │ Defaulted Securities Review                │ KRI_6   │ 999996      │    │
│   │ Effective Leverage: Year Over Year Change  │ KRI_9A  │ 999999      │    │
│   └────────────────────────────────────────────┴─────────┴─────────────┘    │
│                                                                              │
│   Validations-KRI.Validation ──lookup──► KRI Master.KRI Name                │
│                                                   │                          │
│                                                   ├── kriId                  │
│                                                   └── validationId           │
│                                                                              │
│   OPTION B: Auto-Generate (When KRI Master not provided)                     │
│   ──────────────────────────────────────────────────────                     │
│                                                                              │
│   KRIs processed in order of first occurrence:                               │
│   ┌───────────────────────────────────────────┬─────────┬─────────────┐     │
│   │ Order │ KRI Name                          │ KRI ID  │Validation ID│     │
│   ├───────┼───────────────────────────────────┼─────────┼─────────────┤     │
│   │ 1st   │ Interest Expense vs Avg Borrowings│ KRI_1   │ 999991      │     │
│   │ 2nd   │ Defaulted Securities Review       │ KRI_2   │ 999992      │     │
│   │ 3rd   │ Effective Leverage: YoY Change    │ KRI_3   │ 999993      │     │
│   └───────┴───────────────────────────────────┴─────────┴─────────────┘     │
│                                                                              │
│   FORMULA: kriId = "KRI_" + order                                            │
│            validationId = 999990 + order                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Rule 3: Cross-Reference Lookups

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CROSS-REFERENCE LOOKUPS                                   │
│                                                                              │
│   Validations.Fund ────────────────────────────► Funds.Fund ID_New          │
│         │                                                 │                  │
│         │                                                 │                  │
│         │              ┌──────────────────────────────────┤                  │
│         │              │                                  │                  │
│         │              ▼                                  ▼                  │
│         │    ┌─────────────────────────────────────────────────┐            │
│         │    │ LOOKED UP FIELDS:                                │            │
│         │    │                                                  │            │
│         │    │ trust        ◄── Funds.Trust_New                 │            │
│         │    │ book         ◄── Funds.Book_New                  │            │
│         │    │ fundName     ◄── Funds.Book_New (JSON2)          │            │
│         │    │                  Funds.Fund_Name_New (JSON3)     │            │
│         │    │ group        ◄── DERIVED from Fund ID pattern    │            │
│         │    └─────────────────────────────────────────────────┘            │
│         │                                                                    │
│         ▼                                                                    │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │ JSON OUTPUT:                                                       │     │
│   │                                                                    │     │
│   │ {                                                                  │     │
│   │   "trust": "Canada",              // from Funds.Trust_New          │     │
│   │   "fund": "CAN2",                 // from Validations.Fund         │     │
│   │   "fundCode": "CAN2",             // same as fund                  │     │
│   │   "group": "B",                   // derived from CAN2 → 2 → B     │     │
│   │   "book": "Credit Income Fund"    // from Funds.Book_New           │     │
│   │ }                                                                  │     │
│   └───────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Rule 4: Count Calculations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COUNT CALCULATIONS (All from Data)                        │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ rowCount (JSON 1)                                                    │   │
│   │ ═══════════════════                                                  │   │
│   │                                                                      │   │
│   │   rowCount = len(Validations_TRIMMED) + len(Validations_KRI)         │   │
│   │                                                                      │   │
│   │   Example: 1 + 3 = 4                                                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ kriTotalCount (JSON 3, 4)                                            │   │
│   │ ═════════════════════════                                            │   │
│   │                                                                      │   │
│   │   kriTotalCount = len(set(v.validation for v in Validations_KRI))    │   │
│   │                                                                      │   │
│   │   = COUNT(DISTINCT KRI validation names)                             │   │
│   │   = 3 (Interest Expense, Defaulted Securities, Effective Leverage)   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ kriStatusCount per Fund (JSON 3)                                     │   │
│   │ ══════════════════════════════════                                   │   │
│   │                                                                      │   │
│   │   for each fund in Funds:                                            │   │
│   │       count = len([v for v in Validations_KRI                        │   │
│   │                    if v.fund == fund.fund_id_new])                   │   │
│   │                                                                      │   │
│   │   Results:                                                           │   │
│   │   ┌──────────┬───────────────────────────┬─────────┐                │   │
│   │   │ Fund     │ KRI Validations           │ Count   │                │   │
│   │   ├──────────┼───────────────────────────┼─────────┤                │   │
│   │   │ CAN1     │ (none)                    │ 0       │                │   │
│   │   │ CAN2     │ Interest Expense,         │ 2       │                │   │
│   │   │          │ Defaulted Securities      │         │                │   │
│   │   │ CAN3     │ Effective Leverage        │ 1       │                │   │
│   │   └──────────┴───────────────────────────┴─────────┘                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ kriStatusCount Total (JSON 4)                                        │   │
│   │ ═════════════════════════════                                        │   │
│   │                                                                      │   │
│   │   kriStatusCount = len(Validations_KRI)                              │   │
│   │                  = 3                                                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Rule 5: valuesUsedInFormula Construction

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    valuesUsedInFormula (KRI Only)                            │
│                                                                              │
│   SOURCE: KRI Variable Key1-5 and KRI Variable Value1-5 columns              │
│                                                                              │
│   EXCEL DATA:                                                                │
│   ┌─────────────────────────┬───────────────────────────────────────────┐   │
│   │ KRI Variable Key1       │ Average Borrowings                        │   │
│   │ KRI Variable Value1     │ -36711                                    │   │
│   │ KRI Variable Key2       │ Weighted Average Interest Rate            │   │
│   │ KRI Variable Value2     │ 4.38                                      │   │
│   │ KRI Variable Key3       │ Interest Expense                          │   │
│   │ KRI Variable Value3     │ -1633                                     │   │
│   │ KRI Variable Key4       │ (empty)                                   │   │
│   │ KRI Variable Value4     │ (empty)                                   │   │
│   │ KRI Variable Key5       │ (empty)                                   │   │
│   │ KRI Variable Value5     │ (empty)                                   │   │
│   └─────────────────────────┴───────────────────────────────────────────┘   │
│                                                                              │
│   TRANSFORMATION:                                                            │
│   1. Iterate through Key1-5 and Value1-5 pairs                               │
│   2. Skip empty keys or keys with value "--"                                 │
│   3. Parse values as numbers (remove commas)                                 │
│   4. Build ordered dictionary                                                │
│   5. Convert to JSON string                                                  │
│                                                                              │
│   OUTPUT:                                                                    │
│   "{\"Average Borrowings\": -36711.0,                                        │
│     \"Weighted Average Interest Rate\": 4.38,                                │
│     \"Interest Expense\": -1633.0}"                                          │
│                                                                              │
│   NUMBER PARSING:                                                            │
│   • "7,98,606.00" → 798606.0 (removes commas)                               │
│   • "18,17,515.00" → 1817515.0                                              │
│   • "-36711" → -36711.0                                                      │
│   • "4.38" → 4.38                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## ID Consistency Across All JSONs

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ID CONSISTENCY                                         │
│                                                                              │
│   The SAME validationId is used consistently:                                │
│                                                                              │
│   KRI: "Interest Expense versus Average Borrowings"                          │
│                     │                                                        │
│                     ▼                                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ validationId = "999991"  (from KRI Master or auto-generated)         │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                     │                                                        │
│      ┌──────────────┼──────────────┬──────────────┬──────────────┐          │
│      ▼              ▼              ▼              ▼              ▼          │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐        │
│  │ JSON 1 │    │ JSON 2 │    │ JSON 3 │    │ JSON 5 │    │  ALL   │        │
│  │.valid- │    │.fund-  │    │.kri-   │    │.kri-   │    │ USE    │        │
│  │ationId │    │Details │    │Filter  │    │Details │    │ SAME   │        │
│  │        │    │.valid- │    │.valid- │    │.valid- │    │  ID    │        │
│  │        │    │ationId │    │ationId │    │ationId │    │        │        │
│  └────────┘    └────────┘    └────────┘    └────────┘    └────────┘        │
│      │              │              │              │                         │
│      └──────────────┴──────────────┴──────────────┘                         │
│                            │                                                 │
│                            ▼                                                 │
│                   ALL = "999991"                                             │
│                                                                              │
│   Similarly for kriId:                                                       │
│   "Interest Expense..." → kriId = "KRI_1" in JSON 2, 3, 5                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Summary: What's Data-Driven vs Default

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FULLY DATA-DRIVEN (Derived from Excel)                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ ✓ trust            - from Funds.Trust_New                                    │
│ ✓ book             - from Funds.Book_New                                     │
│ ✓ fundName         - from Funds.Book_New or Fund_Name_New                    │
│ ✓ group            - derived from Fund ID_New pattern                        │
│ ✓ fund/fundCode    - from Validations.Fund                                   │
│ ✓ all validation fields - from Validations columns                           │
│ ✓ valuesUsedInFormula - from KRI Variable Key/Value columns                  │
│ ✓ kriId            - from KRI Master or auto-generated                       │
│ ✓ validationId     - from KRI Master or auto-generated                       │
│ ✓ rowCount         - calculated from data                                    │
│ ✓ kriTotalCount    - calculated from data                                    │
│ ✓ kriStatusCount   - calculated from data                                    │
│ ✓ kriDesc          - from Control Procedures column                          │
│ ✓ risk             - from KRI Master (business-provided, NOT calculated)     │
│ ✓ threshold        - from KRI Master (business-provided)                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ CONFIGURABLE DEFAULTS (Can be made data-driven by adding columns)            │
├─────────────────────────────────────────────────────────────────────────────┤
│ • strategy         - default "Credit - Diversified Income"                   │
│                      (add Strategy column to Funds to make data-driven)      │
│ • analyticsStatus  - default "High"                                          │
│ • statusFilter     - default ["Low", "N/A", "High"]                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ BUSINESS-PROVIDED VALUES (from KRI Master)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ • risk             - from KRI Master.Risk (NOT calculated from BPS Impact)   │
│ • threshold        - from KRI Master.Threshold (unique per KRI)              │
│ • riskThresholds   - from KRI Master.Risk Thresholds (optional)              │
│   Example: {"Green": "<2%", "Yellow": "2% - 5%", "Red": ">5%"}               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ALWAYS DEFAULTS (System-generated)                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ • id               - hash generated from validation content                  │
│ • requestId        - UUID generated per request                              │
│ • writeTs          - current timestamp                                       │
│ • auditVersionControlDs - always "1"                                         │
│ • isCpo*, isBannerLess*, isBlueFontControl/Test - always "0"                │
│ • pageInfo         - always { hasNextPage: false, hasPreviousPage: false }  │
└─────────────────────────────────────────────────────────────────────────────┘
```
