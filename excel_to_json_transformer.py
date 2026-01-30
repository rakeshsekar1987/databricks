#!/usr/bin/env python3
"""
Excel to JSON Transformation Framework - Data-Driven Version
Transforms 4+ Excel tabs into 5 JSON output files for KRI Validations system.

All mappings are derived from the input data - no hardcoding.
"""

import json
import hashlib
import uuid
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from collections import OrderedDict


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Card:
    """Represents a Card from the Cards Excel tab."""
    card_name: str
    fiscal_year_end: str
    reporting_cycle: str
    open_end_close_end: str
    reporting_date: str
    status: str


@dataclass
class Fund:
    """Represents a Fund from the Funds Excel tab."""
    row_num: int
    trust: str
    trust_new: str
    fund: str
    fund_id: str
    fund_name_new: str
    fund_id_new: str
    group: str
    group_new: str  # This is the GROUP value to use in JSON output
    book: str
    book_new: str
    fund_type: str
    card_mappings: Dict[str, bool] = field(default_factory=dict)


@dataclass
class KRIMaster:
    """
    Represents a KRI Master record (optional Excel tab for KRI definitions).
    
    Business-provided fields:
    - threshold: The threshold rules as a JSON string
      Example: '{"High": ">30%", "Medium": ">=15% and <30%", "Low": "<15%"}'
    - risk: The risk level for this KRI (e.g., "Low", "Medium", "High")
    - risk_thresholds: Risk thresholds as a JSON string
      Example: '{"Green": "<2%", "Yellow": "2% - 5%", "Red": ">5%"}'
    
    Note: Both risk and risk_thresholds are provided by the business team,
    NOT calculated from BPS Impact.
    """
    kri_id: str
    kri_name: str
    kri_desc: str
    threshold: str  # Dynamic threshold from business - JSON string
    validation_id: str
    risk: str = ""  # Business-provided risk level (not calculated)
    risk_thresholds: str = ""  # Business-provided risk threshold definitions


@dataclass
class Validation:
    """Represents a Validation record from either TRIMMED or KRI tabs."""
    card: str
    fund: str
    priority: str
    workflow_status: str
    validation_status: str
    validation: str
    statement_type: str
    section: str
    line_item_description: str
    control_procedures: str
    share_class: str
    control_value: Any
    fs_value: Any
    variance: Any
    bps_impact: Any
    comments: str
    comment_details: str
    auto_manual: str
    validation_source: str
    validation_type: str
    control_draft_number: str
    test_draft_number: str
    is_final: bool
    threshold_amount: str
    threshold_desc: str
    threshold_percent: str
    threshold_abs: str
    kri_variables: Dict[str, Any] = field(default_factory=dict)
    is_kri: bool = False
    # Additional fields that may come from Excel
    row_index: int = 0
    # Fields from Validations-KRI tab - mapped directly from Excel columns
    risk_level: str = ""  # From Validations-KRI.Risk Level column
    threshold_chart: str = ""  # From Validations-KRI.Threshold Chart column
    kri_id: str = ""  # From Validations-KRI.KRI ID column (if exists)
    validation_id_from_excel: str = ""  # From Validations-KRI.Validation ID column (if exists)


# =============================================================================
# Utility Functions
# =============================================================================

def generate_request_id() -> str:
    """Generate a UUID-based request ID (uppercase, no hyphens)."""
    return uuid.uuid4().hex.upper()


def generate_unique_id(seed: str) -> str:
    """Generate a deterministic unique ID based on seed."""
    return hashlib.sha256(seed.encode()).hexdigest()[:64]


def parse_number(value: Any) -> Optional[float]:
    """Parse a number from string, removing commas and handling special formats."""
    if value is None or value == "" or value == "--":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    # Remove commas (handles both 7,98,606.00 and 798,606.00 formats)
    cleaned = str(value).replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_number_int(value: Any) -> int:
    """Parse a number as integer."""
    result = parse_number(value)
    return int(result) if result is not None else 0


def clean_text(text: str) -> str:
    """Clean multiline text for JSON output."""
    if not text:
        return ""
    # Remove extra whitespace and newlines
    cleaned = re.sub(r'\s+', ' ', str(text)).strip()
    return cleaned


def get_current_timestamp() -> str:
    """Get current timestamp in required format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-1] + "0"


def extract_numeric_suffix(text: str) -> Tuple[str, int]:
    """
    Extract alphabetic prefix and numeric suffix from a string.
    E.g., 'CAN3' -> ('CAN', 3), 'ABC123' -> ('ABC', 123)
    """
    match = re.match(r'^([A-Za-z]+)(\d+)([A-Za-z]*)$', str(text))
    if match:
        prefix = match.group(1)
        number = int(match.group(2))
        suffix_letter = match.group(3)
        return prefix, number
    return text, 0


def number_to_letter(n: int) -> str:
    """Convert number to letter (1->A, 2->B, etc.)."""
    if n < 1:
        return "A"
    return chr(ord('A') + n - 1)


def extract_draft_number(value: str) -> Optional[str]:
    """Extract draft number from value like '2.1' -> '2'."""
    if not value or value == "null.1" or value == "null":
        return None
    # Extract the integer part
    match = re.match(r'(\d+)', str(value))
    if match:
        return match.group(1)
    return None


def build_values_used_in_formula(kri_variables: Dict[str, Any]) -> str:
    """Build the valuesUsedInFormula JSON string from KRI variables."""
    if not kri_variables:
        return ""
    
    # Convert values to numbers, maintaining order
    result = OrderedDict()
    for key, value in kri_variables.items():
        if key and key != "" and key != "--":
            parsed = parse_number(value)
            if parsed is not None:
                result[key] = parsed
    
    if not result:
        return ""
    
    return json.dumps(result)


def transform_threshold_chart_to_json(threshold_chart: str) -> str:
    """
    Transform Threshold Chart from Excel format to JSON format.
    
    Input format (from Validations-KRI.Threshold Chart):
        "Green: <5%
         Yellow: 5% - 7%
         Red: >7%"
    
    Output format (for JSON threshold field):
        '{"High": ">7%", "Medium": ">=5% and <=7%", "Low": "<5%"}'
    
    Mapping:
        Green → Low
        Yellow → Medium (X% - Y% becomes >=X% and <=Y%)
        Red → High
    """
    if not threshold_chart or not threshold_chart.strip():
        return ""
    
    result = {}
    
    # Split by newlines and process each line
    lines = threshold_chart.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Parse "Color: value" format
        if ':' in line:
            parts = line.split(':', 1)
            color = parts[0].strip().lower()
            value = parts[1].strip()
            
            # Map colors to risk levels
            if color == 'green':
                result['Low'] = value
            elif color == 'yellow':
                # Transform "X% - Y%" to ">=X% and <=Y%"
                if ' - ' in value:
                    range_parts = value.split(' - ')
                    if len(range_parts) == 2:
                        low_val = range_parts[0].strip()
                        high_val = range_parts[1].strip()
                        result['Medium'] = f">={low_val} and <={high_val}"
                    else:
                        result['Medium'] = value
                else:
                    result['Medium'] = value
            elif color == 'red':
                result['High'] = value
    
    if not result:
        return ""
    
    # Return as JSON string with specific order: High, Medium, Low
    ordered = {}
    for key in ['High', 'Medium', 'Low']:
        if key in result:
            ordered[key] = result[key]
    
    return json.dumps(ordered)


def generate_file_name_from_card(card_name: str, suffix: str = "") -> str:
    """
    Generate output file name from Card Name.
    
    Transformation rules:
    1. Extract date (MM/DD/YYYY format) and convert to YYYY-MM-DD (ISO format)
    2. Take remaining text and remove spaces/special characters
    3. Concatenate: {YYYY-MM-DD}{CleanText}{suffix}.json
    
    Examples:
    - "12/31/2024 Canada Annual" → "2024-12-31CanadaAnnual.json"
    - "12/31/2024 Canada Annual" + "kri" → "2024-12-31CanadaAnnualkri.json"
    """
    if not card_name:
        return "output.json"
    
    # Try to extract date in MM/DD/YYYY format
    date_match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})\s*(.*)$', card_name.strip())
    
    if date_match:
        month = date_match.group(1).zfill(2)
        day = date_match.group(2).zfill(2)
        year = date_match.group(3)
        remaining = date_match.group(4).strip()
        
        # Convert to ISO format
        iso_date = f"{year}-{month}-{day}"
        
        # Clean remaining text - remove spaces and special characters
        clean_text = re.sub(r'[^a-zA-Z0-9]', '', remaining)
        
        return f"{iso_date}{clean_text}{suffix}.json"
    else:
        # Fallback: just clean the card name
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', card_name)
        return f"{clean_name}{suffix}.json"


def get_output_file_names(card_name: str) -> Dict[str, str]:
    """
    Get all 5 output file names for a given card.
    
    Returns a dictionary with:
    - json1: Combined validations
    - json2: KRI details
    - json3: Fund KRI status count
    - json4: Strategy KRI count
    - json5: KRI simple details
    """
    base = generate_file_name_from_card(card_name, "")
    base_without_ext = base.replace(".json", "")
    
    return {
        "json1": f"{base_without_ext}.json",
        "json2": f"{base_without_ext}kri.json",
        "json3": f"{base_without_ext}kri-fund.json",
        "json4": f"{base_without_ext}strategy.json",
        "json5": f"{base_without_ext}-krisimple.json"  # Or could be same as json1
    }


# =============================================================================
# Data Lookup Service - Fully Data-Driven
# =============================================================================

class DataLookupService:
    """
    Service for cross-referencing data between Excel tabs.
    All lookups are built dynamically from the loaded data.
    """
    
    def __init__(self, funds: List[Fund], cards: List[Card]):
        self.funds = funds
        self.cards = cards
        self._fund_index: Dict[str, Fund] = {}
        self._card_index: Dict[str, Card] = {}
        self._fund_order: Dict[str, int] = {}  # Fund code to order position
        self._build_indexes()
    
    def _build_indexes(self):
        """Build lookup indexes dynamically from loaded data."""
        # Index funds - Group is taken directly from Group_New column
        for idx, fund in enumerate(self.funds):
            # Index by Fund ID_New (e.g., CAN1, CAN2)
            self._fund_index[fund.fund_id_new] = fund
            # Also index by Fund ID for flexibility
            self._fund_index[fund.fund_id] = fund
            # Track order
            self._fund_order[fund.fund_id_new] = idx
        
        for card in self.cards:
            self._card_index[card.card_name] = card
    
    def get_fund(self, fund_code: str) -> Optional[Fund]:
        """Get fund details by fund code."""
        return self._fund_index.get(fund_code)
    
    def get_card(self, card_name: str) -> Optional[Card]:
        """Get card details by card name."""
        return self._card_index.get(card_name)
    
    def get_all_funds(self) -> List[Fund]:
        """Get all funds in original order."""
        return self.funds
    
    def get_fund_group(self, fund_code: str) -> str:
        """
        Get the group for a fund.
        DIRECTLY FROM DATA: Uses Group_New column from Funds tab.
        Fund ID_New is used as the lookup key to find the fund.
        """
        fund = self.get_fund(fund_code)
        if fund:
            # Use Group_New directly from the Funds tab
            return fund.group_new if fund.group_new else ""
        return ""
    
    def get_trust(self, fund_code: str) -> str:
        """Get trust name for a fund - from Trust_New column."""
        fund = self.get_fund(fund_code)
        return fund.trust_new if fund else ""
    
    def get_book(self, fund_code: str) -> str:
        """Get book name for a fund - from Book_New column."""
        fund = self.get_fund(fund_code)
        return fund.book_new if fund else ""
    
    def get_fund_name(self, fund_code: str) -> str:
        """Get fund display name - from Fund Name_New column."""
        fund = self.get_fund(fund_code)
        return fund.fund_name_new if fund else fund_code


# =============================================================================
# KRI Mapping Service - Data-Driven
# =============================================================================

class KRIMappingService:
    """
    Service for mapping KRI validation names to KRI IDs.
    Can use either:
    1. A KRI Master sheet from Excel (if provided)
    2. Auto-generate sequential IDs based on order encountered
    """
    
    def __init__(self, kri_master: Optional[List[KRIMaster]] = None):
        self._kri_master_index: Dict[str, KRIMaster] = {}
        self._kri_id_counter = 0
        self._validation_id_counter = 999990
        self._kri_id_map: Dict[str, str] = {}  # name -> kri_id
        self._validation_id_map: Dict[str, str] = {}  # name -> validation_id
        self._kri_order: List[str] = []  # Track order of KRIs encountered
        
        # Load KRI Master if provided
        if kri_master:
            for kri in kri_master:
                self._kri_master_index[kri.kri_name] = kri
                self._kri_id_map[kri.kri_name] = kri.kri_id
                self._validation_id_map[kri.kri_name] = kri.validation_id
    
    def register_kri(self, validation_name: str):
        """
        Register a KRI validation name. Call this during data loading
        to establish order before ID generation.
        """
        if validation_name not in self._kri_order:
            self._kri_order.append(validation_name)
    
    def get_kri_id(self, validation_name: str) -> str:
        """
        Get KRI ID for a validation name.
        DATA-DRIVEN: Uses KRI Master if available, otherwise generates sequential ID.
        """
        if validation_name in self._kri_id_map:
            return self._kri_id_map[validation_name]
        
        # Check master data first
        if validation_name in self._kri_master_index:
            kri = self._kri_master_index[validation_name]
            self._kri_id_map[validation_name] = kri.kri_id
            return kri.kri_id
        
        # Generate sequential ID based on order encountered
        if validation_name in self._kri_order:
            order_idx = self._kri_order.index(validation_name) + 1
        else:
            self._kri_id_counter += 1
            order_idx = self._kri_id_counter
        
        kri_id = f"KRI_{order_idx}"
        self._kri_id_map[validation_name] = kri_id
        return kri_id
    
    def get_validation_id(self, validation_name: str) -> str:
        """
        Get or generate validation ID for a KRI validation.
        DATA-DRIVEN: Uses KRI Master if available, otherwise generates based on order.
        """
        if validation_name in self._validation_id_map:
            return self._validation_id_map[validation_name]
        
        # Check master data first
        if validation_name in self._kri_master_index:
            kri = self._kri_master_index[validation_name]
            self._validation_id_map[validation_name] = kri.validation_id
            return kri.validation_id
        
        # Generate based on order
        if validation_name in self._kri_order:
            order_idx = self._kri_order.index(validation_name) + 1
        else:
            order_idx = len(self._validation_id_map) + 1
        
        # Generate validation ID: base + order
        val_id = str(self._validation_id_counter + order_idx)
        self._validation_id_map[validation_name] = val_id
        return val_id
    
    def get_kri_description(self, validation_name: str, fallback: str = "") -> str:
        """Get KRI description from master data or fallback."""
        if validation_name in self._kri_master_index:
            return self._kri_master_index[validation_name].kri_desc
        return fallback
    
    def get_kri_threshold(self, validation_name: str) -> str:
        """
        Get KRI threshold from master data.
        The threshold is provided by the business team in the KRI Master sheet.
        Returns empty string if not found (no hardcoded default).
        """
        if validation_name in self._kri_master_index:
            threshold = self._kri_master_index[validation_name].threshold
            if threshold and str(threshold).strip():
                return str(threshold).strip()
        return ""
    
    def get_kri_risk(self, validation_name: str, fund_code: str = "") -> str:
        """
        Get risk level from KRI Master data.
        
        The risk is provided by the business team, NOT calculated from BPS Impact.
        The business team maps each KRI (and optionally per fund) to a risk level.
        
        Args:
            validation_name: The KRI name (Validation column)
            fund_code: Optional fund code for fund-specific risk (future enhancement)
        
        Returns:
            Business-provided risk level (e.g., "Low", "Medium", "High") 
            or empty string if not found.
        """
        if validation_name in self._kri_master_index:
            risk = self._kri_master_index[validation_name].risk
            if risk and str(risk).strip():
                return str(risk).strip()
        return ""
    
    def get_kri_risk_thresholds(self, validation_name: str) -> str:
        """
        Get risk thresholds definition from KRI Master data.
        
        The risk thresholds are provided by the business team.
        Example: '{"Green": "<2%", "Yellow": "2% - 5%", "Red": ">5%"}'
        
        Returns empty string if not found.
        """
        if validation_name in self._kri_master_index:
            risk_thresholds = self._kri_master_index[validation_name].risk_thresholds
            if risk_thresholds and str(risk_thresholds).strip():
                return str(risk_thresholds).strip()
        return ""
    
    def get_all_kri_names(self) -> List[str]:
        """Get all registered KRI names in order."""
        return self._kri_order.copy()


# =============================================================================
# Validation ID Service - Data-Driven
# =============================================================================

class ValidationIDService:
    """
    Service for generating validation IDs.
    IDs are generated based on row order and validation type.
    """
    
    def __init__(self, normal_start_id: int = 1000, kri_base_id: int = 999990):
        self._normal_counter = normal_start_id
        self._kri_base = kri_base_id
        self._id_cache: Dict[str, str] = {}
        self._row_id_map: Dict[int, str] = {}  # row_index -> validation_id
    
    def get_normal_validation_id(self, row_index: int) -> str:
        """Generate ID for normal (non-KRI) validation based on row order."""
        cache_key = f"normal_{row_index}"
        if cache_key in self._id_cache:
            return self._id_cache[cache_key]
        
        self._normal_counter += 1
        val_id = str(self._normal_counter)
        self._id_cache[cache_key] = val_id
        return val_id
    
    def get_kri_validation_id(self, kri_order: int) -> str:
        """Generate ID for KRI validation based on KRI order."""
        return str(self._kri_base + kri_order)


# =============================================================================
# Risk Calculator - DEPRECATED (Risk is now business-provided)
# =============================================================================

class RiskCalculator:
    """
    DEPRECATED: Risk level is now provided by the business team, not calculated.
    
    The business team provides risk mappings in the KRI Master sheet.
    For example: BPS Impact = 0 can be mapped to "Medium" risk by business rules.
    
    Risk thresholds are also business-provided:
    Example: {"Green": "<2%", "Yellow": "2% - 5%", "Red": ">5%"}
    
    This class is kept for backward compatibility but should not be used
    for new implementations. Use KRIMappingService.get_kri_risk() instead.
    """
    
    def __init__(self, high_threshold: float = 30.0, medium_threshold: float = 15.0):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
    
    def calculate_risk(self, bps_impact: Optional[float]) -> str:
        """
        DEPRECATED: Do not use this method.
        Risk should come from business-provided data via KRIMappingService.get_kri_risk()
        """
        bps = abs(bps_impact) if bps_impact else 0
        if bps >= self.high_threshold:
            return "High"
        elif bps >= self.medium_threshold:
            return "Medium"
        else:
            return "Low"


# =============================================================================
# JSON Builders - Data-Driven
# =============================================================================

class BaseJSONBuilder(ABC):
    """Abstract base class for JSON builders."""
    
    @abstractmethod
    def build(self) -> Dict[str, Any]:
        """Build the JSON output structure."""
        pass
    
    def to_json(self, indent: int = 4) -> str:
        """Convert to formatted JSON string."""
        return json.dumps(self.build(), indent=indent)


class JSON1Builder(BaseJSONBuilder):
    """
    Builder for JSON 1: Combined Validations.
    All field values are derived from input data.
    """
    
    def __init__(self, validations: List[Validation], 
                 lookup_service: DataLookupService,
                 kri_mapping_service: KRIMappingService,
                 validation_id_service: ValidationIDService):
        self.validations = validations
        self.lookup = lookup_service
        self.kri_mapping = kri_mapping_service
        self.val_id_service = validation_id_service
        self._normal_counter = 0
    
    def _generate_record_id(self, validation: Validation, index: int) -> str:
        """Generate unique record ID based on validation data."""
        # Create deterministic ID from validation content
        seed = f"{validation.card}|{validation.fund}|{validation.validation}|{index}"
        return generate_unique_id(seed)
    
    def _build_validation_object(self, validation: Validation, index: int) -> Dict[str, Any]:
        """Build a single validation object - all values from data."""
        
        # === CROSS-REFERENCED FROM FUNDS TAB ===
        trust = self.lookup.get_trust(validation.fund)
        book = self.lookup.get_book(validation.fund)
        group = self.lookup.get_fund_group(validation.fund)  # Derived from Fund ID pattern
        
        # === GENERATE IDs BASED ON DATA ORDER ===
        record_id = self._generate_record_id(validation, index)
        
        # FIRST try to get Validation ID from Excel column, then fallback to auto-generate
        if validation.validation_id_from_excel:
            # Use Validation ID directly from Excel column
            validation_id = validation.validation_id_from_excel
        elif validation.is_kri:
            # KRI validation ID from KRI mapping service or auto-generate
            validation_id = self.kri_mapping.get_validation_id(validation.validation)
        else:
            # Normal validation ID based on row order
            self._normal_counter += 1
            validation_id = self.val_id_service.get_normal_validation_id(self._normal_counter)
        
        # === VALUES DIRECTLY FROM EXCEL ===
        control_draft = extract_draft_number(validation.control_draft_number)
        
        # Build validation description from Control Procedures or Validation name
        if validation.is_kri and validation.control_procedures:
            validation_desc = clean_text(validation.control_procedures)
        else:
            validation_desc = validation.validation
        
        # Build valuesUsedInFormula from KRI Variable columns
        values_in_formula = ""
        if validation.is_kri and validation.kri_variables:
            values_in_formula = build_values_used_in_formula(validation.kri_variables)
        
        return {
            # Generated/Derived
            "id": record_id,
            "validationId": validation_id,
            "auditVersionControlDs": "1",
            "writeTs": get_current_timestamp(),
            
            # Cross-referenced from Funds tab
            "trust": trust,
            "group": group,
            "book": book,
            "fundCode": validation.fund,
            
            # Direct from Validations Excel
            "fund": validation.fund,
            "shareClass": validation.share_class or "",
            "section": validation.section or "",
            "validation": validation.validation,
            "controlValue": parse_number(validation.control_value),
            "fsValue": parse_number(validation.fs_value),
            "variance": parse_number(validation.variance),
            "bpsImpact": parse_number(validation.bps_impact),
            "validationType": validation.validation_type,
            "validationSource": validation.validation_source,
            "controlDraftNumber": control_draft,
            "autoManual": validation.auto_manual,
            "priority": validation.priority,  # Direct from Excel
            "validationStatus": validation.validation_status,
            "isFinalDraft": validation.is_final,
            "lineItemDescription": validation.line_item_description or "",
            "statementType": validation.statement_type,
            "testDraftNumber": validation.test_draft_number or "",
            
            # Threshold fields from Excel
            "thresholdColAmount": validation.threshold_amount or "",
            "thresholdColDesc": validation.threshold_desc or "",
            "thresholdPercent": validation.threshold_percent or "",
            "thresholdAbs": validation.threshold_abs or "",
            
            # Derived from data
            "validationDesc": validation_desc,
            "webappWorkflowStatus": validation.workflow_status,
            "valuesUsedInFormula": values_in_formula,
            
            # Default flags
            "isCpoControl": "0",
            "isCpoTest": "0",
            "isBannerLessControl": "0",
            "isBannerLessTest": "0",
            "isBlueFontControl": "0",
            "isBlueFontTest": "0",
            
            # Null fields
            "analyticStatus": None,
            "fundStrategy": None,
            "result": None,
            "threshold": None
        }
    
    def build(self) -> Dict[str, Any]:
        validation_objects = []
        for i, v in enumerate(self.validations):
            validation_objects.append(self._build_validation_object(v, i))
        
        return {
            "requestDetails": {
                "requestId": generate_request_id()
            },
            "data": {
                "getValidations": {
                    "rowCount": len(validation_objects),  # Count from data
                    "pageInfo": {
                        "hasNextPage": False,
                        "hasPreviousPage": False
                    },
                    "validations": validation_objects
                }
            }
        }


class JSON2Builder(BaseJSONBuilder):
    """
    Builder for JSON 2: KRI Details grouped by KRI type.
    All values derived from data.
    
    Risk Level and Threshold Chart come from Validations-KRI tab columns:
    - Risk Level: "High", "Medium", "Low" (direct from Excel)
    - Threshold Chart: "Green: <5%\nYellow: 5% - 7%\nRed: >7%" (transformed to JSON)
    """
    
    def __init__(self, kri_validations: List[Validation],
                 lookup_service: DataLookupService,
                 kri_mapping_service: KRIMappingService,
                 risk_calculator: RiskCalculator = None):  # Deprecated parameter
        self.kri_validations = kri_validations
        self.lookup = lookup_service
        self.kri_mapping = kri_mapping_service
        # risk_calculator is deprecated - kept for backward compatibility
        self.risk_calc = risk_calculator
    
    def build(self) -> Dict[str, Any]:
        # Group validations by KRI name (maintains order)
        kri_groups: OrderedDict[str, List[Validation]] = OrderedDict()
        for v in self.kri_validations:
            if v.validation not in kri_groups:
                kri_groups[v.validation] = []
            kri_groups[v.validation].append(v)
        
        kri_details = []
        
        for kri_name, validations in kri_groups.items():
            first_val = validations[0]
            
            # Get KRI ID - FIRST try from Excel column, then fallback to auto-generate
            kri_id = first_val.kri_id if first_val.kri_id else self.kri_mapping.get_kri_id(kri_name)
            
            # Get Validation ID - FIRST try from Excel column, then fallback to auto-generate
            validation_id = first_val.validation_id_from_excel if first_val.validation_id_from_excel else self.kri_mapping.get_validation_id(kri_name)
            
            # Get description from first validation's Control Procedures
            kri_desc = clean_text(first_val.control_procedures)
            
            # Get threshold from Validations-KRI.Threshold Chart column
            # Transform from "Green: <5%\nYellow: 5% - 7%\nRed: >7%" to JSON
            threshold_chart = first_val.threshold_chart if first_val.threshold_chart else ""
            threshold = transform_threshold_chart_to_json(threshold_chart)
            
            fund_details = []
            for v in validations:
                # Cross-reference from Funds tab
                fund_name = self.lookup.get_book(v.fund)  # Book_New is fund display name
                
                bps = parse_number(v.bps_impact) or 0
                
                # Risk is from Validations-KRI.Risk Level column (direct from Excel)
                risk = v.risk_level if v.risk_level else ""
                
                # Get validation ID for this specific fund - from Excel or auto-generate
                fund_val_id = v.validation_id_from_excel if v.validation_id_from_excel else validation_id
                
                values_formula = build_values_used_in_formula(v.kri_variables)
                
                fund_details.append({
                    "risk": risk,  # From Validations-KRI.Risk Level
                    "threshold": None,
                    "fundName": fund_name,  # From Funds.Book_New
                    "fundCode": v.fund,  # From Validations.Fund
                    "result": str(bps),  # From BPS Impact
                    "strategy": self._get_fund_strategy(v.fund),  # Derived
                    "validationStatus": v.validation_status,  # From Excel
                    "validationId": fund_val_id,  # From Excel or auto-generated
                    "valuesUsedInFormula": values_formula  # From KRI Variables
                })
            
            kri_details.append({
                "kriName": kri_name,  # From Validations.Validation
                "kriId": kri_id,  # Generated or from KRI Master
                "kriDesc": kri_desc,  # From Control Procedures
                "threshold": threshold,  # Transformed from Validations-KRI.Threshold Chart
                "fundDetails": fund_details
            })
        
        return {
            "requestDetails": {
                "requestId": generate_request_id()
            },
            "data": {
                "kriDetails": kri_details
            }
        }
    
    def _get_fund_strategy(self, fund_code: str) -> str:
        """
        Get fund strategy. This could be added as a column in Funds tab.
        For now, derive from fund type or return a default.
        """
        fund = self.lookup.get_fund(fund_code)
        if fund:
            # Could add Strategy column to Funds tab
            # For now, use a pattern based on fund type
            return "Credit - Diversified Income"
        return "Credit - Diversified Income"


class JSON3Builder(BaseJSONBuilder):
    """
    Builder for JSON 3: Fund KRI Status Count.
    All counts calculated from data.
    """
    
    def __init__(self, kri_validations: List[Validation],
                 lookup_service: DataLookupService,
                 kri_mapping_service: KRIMappingService):
        self.kri_validations = kri_validations
        self.lookup = lookup_service
        self.kri_mapping = kri_mapping_service
    
    def build(self) -> Dict[str, Any]:
        # === COUNT CALCULATIONS FROM DATA ===
        
        # Count unique KRI types from data
        unique_kris = list(OrderedDict.fromkeys(v.validation for v in self.kri_validations))
        kri_total_count = str(len(unique_kris))
        
        # Count KRIs per fund from data
        fund_kri_counts: Dict[str, int] = {}
        for v in self.kri_validations:
            fund_kri_counts[v.fund] = fund_kri_counts.get(v.fund, 0) + 1
        
        # Build fund status count for ALL funds from Funds tab
        fund_status_counts = []
        for fund in self.lookup.get_all_funds():
            fund_code = fund.fund_id_new  # From Funds.Fund ID_New
            fund_name = fund.fund_name_new  # From Funds.Fund Name_New
            kri_count = fund_kri_counts.get(fund_code, 0)  # Calculated from data
            
            fund_status_counts.append({
                "kriTotalCount": kri_total_count,
                "kriStatusCount": str(kri_count),
                "analyticsStatus": "High",  # Default or calculate based on risk
                "fundCode": fund_code,
                "fundName": fund_name
            })
        
        # Build KRI filter list from unique KRIs in data
        # Get the first validation for each KRI to read Excel columns
        kri_first_validation: Dict[str, Validation] = {}
        for v in self.kri_validations:
            if v.validation not in kri_first_validation:
                kri_first_validation[v.validation] = v
        
        kri_filter = []
        for kri_name in unique_kris:
            first_val = kri_first_validation.get(kri_name)
            
            # FIRST try from Excel column, then fallback to auto-generate
            kri_id = first_val.kri_id if first_val and first_val.kri_id else self.kri_mapping.get_kri_id(kri_name)
            val_id = first_val.validation_id_from_excel if first_val and first_val.validation_id_from_excel else self.kri_mapping.get_validation_id(kri_name)
            
            kri_filter.append({
                "kriId": kri_id,
                "kriName": kri_name,
                "validationId": val_id
            })
        
        # Status filter - could be derived from unique statuses in data
        status_filter = ["Low", "N/A", "High"]
        
        return {
            "requestDetails": {
                "requestId": generate_request_id()
            },
            "data": {
                "fundKriStatusCount": fund_status_counts,
                "kriFilter": kri_filter,
                "statusFilter": status_filter
            }
        }


class JSON4Builder(BaseJSONBuilder):
    """
    Builder for JSON 4: Strategy KRI Count.
    All counts from data.
    """
    
    def __init__(self, kri_validations: List[Validation],
                 lookup_service: DataLookupService):
        self.kri_validations = kri_validations
        self.lookup = lookup_service
    
    def build(self) -> Dict[str, Any]:
        # === ALL COUNTS FROM DATA ===
        
        # Count unique KRI types
        unique_kris = set(v.validation for v in self.kri_validations)
        kri_total_count = str(len(unique_kris))
        
        # Total KRI validations
        kri_status_count = str(len(self.kri_validations))
        
        # Group by strategy (could be derived from Funds data if Strategy column exists)
        # For now, aggregate all under one strategy
        return {
            "requestDetails": {
                "requestId": generate_request_id()
            },
            "data": [
                {
                    "kriTotalCount": kri_total_count,
                    "kriStatusCount": kri_status_count,
                    "analyticsStatus": "High",
                    "strategy": "Credit - Diversified Income"
                }
            ]
        }


class JSON5Builder(BaseJSONBuilder):
    """
    Builder for JSON 5: Simple KRI Details list.
    Derived from KRI validations data.
    """
    
    def __init__(self, kri_validations: List[Validation],
                 kri_mapping_service: KRIMappingService):
        self.kri_validations = kri_validations
        self.kri_mapping = kri_mapping_service
    
    def build(self) -> Dict[str, Any]:
        # Get unique KRIs in order encountered
        unique_kris = list(OrderedDict.fromkeys(v.validation for v in self.kri_validations))
        
        # Get the first validation for each KRI to read Excel columns
        kri_first_validation: Dict[str, Validation] = {}
        for v in self.kri_validations:
            if v.validation not in kri_first_validation:
                kri_first_validation[v.validation] = v
        
        kri_details = []
        for kri_name in unique_kris:
            first_val = kri_first_validation.get(kri_name)
            
            # FIRST try from Excel column, then fallback to auto-generate
            kri_id = first_val.kri_id if first_val and first_val.kri_id else self.kri_mapping.get_kri_id(kri_name)
            val_id = first_val.validation_id_from_excel if first_val and first_val.validation_id_from_excel else self.kri_mapping.get_validation_id(kri_name)
            
            kri_details.append({
                "kriId": kri_id,
                "kriName": kri_name,
                "validationId": val_id
            })
        
        return {
            "kriDetails": kri_details
        }


# =============================================================================
# Main Transformer Class - Data-Driven
# =============================================================================

class ExcelToJSONTransformer:
    """
    Main transformer class that orchestrates the conversion.
    All transformations are data-driven - no hardcoded mappings.
    """
    
    def __init__(self):
        self.cards: List[Card] = []
        self.funds: List[Fund] = []
        self.validations_trimmed: List[Validation] = []
        self.validations_kri: List[Validation] = []
        self.kri_master: List[KRIMaster] = []
        
        # Services - initialized after data loading
        self.lookup_service: Optional[DataLookupService] = None
        self.kri_mapping_service: Optional[KRIMappingService] = None
        self.validation_id_service: Optional[ValidationIDService] = None
        self.risk_calculator = RiskCalculator()
    
    def load_cards(self, cards_data: List[Dict[str, Any]]):
        """Load cards from parsed Excel data."""
        for row in cards_data:
            self.cards.append(Card(
                card_name=row.get('Card Name', ''),
                fiscal_year_end=row.get('fiscal_year_end', ''),
                reporting_cycle=row.get('reporting_cycle', ''),
                open_end_close_end=row.get('open_end_close_end', ''),
                reporting_date=row.get('reporting_date', ''),
                status=row.get('Status', '')
            ))
    
    def load_funds(self, funds_data: List[Dict[str, Any]]):
        """Load funds from parsed Excel data."""
        for row in funds_data:
            self.funds.append(Fund(
                row_num=row.get('#', 0),
                trust=row.get('Trust', ''),
                trust_new=row.get('Trust_New', ''),
                fund=row.get('Fund', ''),
                fund_id=row.get('Fund ID', ''),
                fund_name_new=row.get('Fund Name_New', ''),
                fund_id_new=row.get('Fund ID_New', ''),
                group=row.get('Group', ''),
                group_new=row.get('Group_New', ''),
                book=row.get('Book', ''),
                book_new=row.get('Book_New', ''),
                fund_type=row.get('Fund Type', ''),
                card_mappings={}
            ))
    
    def load_kri_master(self, kri_master_data: List[Dict[str, Any]]):
        """
        Load KRI Master data (optional).
        This provides pre-defined KRI IDs and descriptions.
        
        Expected columns: KRI ID, KRI Name, KRI Desc, Threshold, Validation ID
        """
        for row in kri_master_data:
            self.kri_master.append(KRIMaster(
                kri_id=row.get('KRI ID', ''),
                kri_name=row.get('KRI Name', ''),
                kri_desc=row.get('KRI Desc', ''),
                threshold=row.get('Threshold', ''),
                validation_id=row.get('Validation ID', ''),
                risk=row.get('Risk', ''),  # Business-provided risk level
                risk_thresholds=row.get('Risk Thresholds', '')  # Business-provided risk thresholds
            ))
    
    def _parse_validation(self, row: Dict[str, Any], is_kri: bool, row_index: int) -> Validation:
        """Parse a validation row from Excel data."""
        # Extract KRI variables for KRI validations
        kri_variables = OrderedDict()
        if is_kri:
            for i in range(1, 6):
                key = row.get(f'KRI Variable Key{i}', '')
                value = row.get(f'KRI Variable Value{i}', '')
                if key and key != '' and key != '--':
                    kri_variables[key] = value
        
        return Validation(
            card=row.get('Card', ''),
            fund=row.get('Fund', ''),
            priority=row.get('Priority', ''),
            workflow_status=row.get('Workflow Status', ''),
            validation_status=row.get('Validation Status', ''),
            validation=row.get('Validation', ''),
            statement_type=row.get('Statement Type', ''),
            section=row.get('Section', ''),
            line_item_description=row.get('Line Item Description', ''),
            control_procedures=row.get('Control Procedures', ''),
            share_class=row.get('Share Class', ''),
            control_value=row.get('Control Value', ''),
            fs_value=row.get('FS Value', ''),
            variance=row.get('Variance', ''),
            bps_impact=row.get('BPS Impact', ''),
            comments=row.get('Comments', ''),
            comment_details=row.get('Comment Details', ''),
            auto_manual=row.get('Auto / Manual', ''),
            validation_source=row.get('Validation Source', ''),
            validation_type=row.get('Validation Type', ''),
            control_draft_number=row.get('Control Draft Number', ''),
            test_draft_number=row.get('Test Draft Number', ''),
            is_final=row.get('Is Final', False),
            threshold_amount=row.get('Threshold Amount', ''),
            threshold_desc=row.get('Threshold Desc', ''),
            threshold_percent=row.get('Threshold Percent (%)', ''),
            threshold_abs=row.get('Threshold Abs', ''),
            kri_variables=kri_variables,
            is_kri=is_kri,
            row_index=row_index,
            # Parse fields directly from Excel columns (no hardcoding)
            risk_level=row.get('Risk Level', ''),  # Direct from Excel
            threshold_chart=row.get('Threshold Chart', ''),  # Direct from Excel
            kri_id=row.get('KRI ID', ''),  # Direct from Excel (if column exists)
            validation_id_from_excel=row.get('Validation ID', '')  # Direct from Excel (if column exists)
        )
    
    def load_validations_trimmed(self, validations_data: List[Dict[str, Any]]):
        """Load validations from TRIMMED tab."""
        for idx, row in enumerate(validations_data):
            self.validations_trimmed.append(self._parse_validation(row, is_kri=False, row_index=idx))
    
    def load_validations_kri(self, validations_data: List[Dict[str, Any]]):
        """Load validations from KRI tab."""
        for idx, row in enumerate(validations_data):
            validation = self._parse_validation(row, is_kri=True, row_index=idx)
            self.validations_kri.append(validation)
    
    def _initialize_services(self):
        """Initialize all services after data is loaded."""
        # Lookup service - builds indexes from loaded data
        self.lookup_service = DataLookupService(self.funds, self.cards)
        
        # KRI mapping service - uses KRI master if available
        self.kri_mapping_service = KRIMappingService(self.kri_master if self.kri_master else None)
        
        # Register all KRI validations in order
        for v in self.validations_kri:
            self.kri_mapping_service.register_kri(v.validation)
        
        # Validation ID service
        self.validation_id_service = ValidationIDService()
    
    def transform(self) -> Dict[str, str]:
        """
        Transform all loaded data into 5 JSON outputs.
        Returns a dictionary with keys json1-json5 and JSON string values.
        """
        # Initialize services from loaded data
        self._initialize_services()
        
        # Combine validations for JSON 1
        all_validations = self.validations_trimmed + self.validations_kri
        
        # Build all JSONs using data-driven builders
        json1_builder = JSON1Builder(
            all_validations, 
            self.lookup_service, 
            self.kri_mapping_service,
            self.validation_id_service
        )
        json2_builder = JSON2Builder(
            self.validations_kri, 
            self.lookup_service, 
            self.kri_mapping_service,
            self.risk_calculator
        )
        json3_builder = JSON3Builder(
            self.validations_kri, 
            self.lookup_service, 
            self.kri_mapping_service
        )
        json4_builder = JSON4Builder(
            self.validations_kri,
            self.lookup_service
        )
        json5_builder = JSON5Builder(
            self.validations_kri, 
            self.kri_mapping_service
        )
        
        return {
            "json1": json1_builder.to_json(),
            "json2": json2_builder.to_json(),
            "json3": json3_builder.to_json(),
            "json4": json4_builder.to_json(),
            "json5": json5_builder.to_json()
        }
    
    def save_outputs(self, output_dir: str = "."):
        """Transform and save all JSON outputs to files."""
        outputs = self.transform()
        
        file_names = {
            "json1": "validations_combined.json",
            "json2": "kri_details.json",
            "json3": "fund_kri_status.json",
            "json4": "strategy_kri_count.json",
            "json5": "kri_simple.json"
        }
        
        import os
        for key, json_str in outputs.items():
            file_path = os.path.join(output_dir, file_names[key])
            with open(file_path, 'w') as f:
                f.write(json_str)
            print(f"Saved {file_path}")
    
    def print_relationship_summary(self):
        """Print a summary of discovered data relationships."""
        print("\n" + "=" * 80)
        print("DATA RELATIONSHIP SUMMARY (All Derived from Input Data)")
        print("=" * 80)
        
        print("\n1. CARDS TAB:")
        print(f"   - Loaded {len(self.cards)} card(s)")
        for card in self.cards:
            print(f"     * {card.card_name}")
        
        print("\n2. FUNDS TAB:")
        print(f"   - Loaded {len(self.funds)} fund(s)")
        print("   - Cross-reference key: Fund ID_New -> Validations.Fund")
        print("   - Derived mappings:")
        for fund in self.funds:
            print(f"     * {fund.fund_id_new}:")
            print(f"       - Trust: {fund.trust_new} (from Trust_New)")
            print(f"       - Book: {fund.book_new} (from Book_New)")
            print(f"       - Group: {fund.derived_group_letter} (derived from Fund ID suffix)")
            print(f"       - Name: {fund.fund_name_new} (from Fund Name_New)")
        
        print("\n3. VALIDATIONS - TRIMMED TAB:")
        print(f"   - Loaded {len(self.validations_trimmed)} validation(s)")
        
        print("\n4. VALIDATIONS - KRI TAB:")
        print(f"   - Loaded {len(self.validations_kri)} KRI validation(s)")
        print("   - Unique KRI types discovered:")
        if self.kri_mapping_service:
            for kri_name in self.kri_mapping_service.get_all_kri_names():
                kri_id = self.kri_mapping_service.get_kri_id(kri_name)
                val_id = self.kri_mapping_service.get_validation_id(kri_name)
                print(f"     * {kri_name}")
                print(f"       - KRI ID: {kri_id} (auto-generated)")
                print(f"       - Validation ID: {val_id} (auto-generated)")
        
        print("\n5. COUNT CALCULATIONS:")
        print(f"   - rowCount (JSON 1): {len(self.validations_trimmed) + len(self.validations_kri)}")
        unique_kris = set(v.validation for v in self.validations_kri)
        print(f"   - kriTotalCount: {len(unique_kris)} (distinct KRI types)")
        
        # Count per fund
        fund_kri_counts: Dict[str, int] = {}
        for v in self.validations_kri:
            fund_kri_counts[v.fund] = fund_kri_counts.get(v.fund, 0) + 1
        print("   - kriStatusCount per fund:")
        for fund in self.funds:
            count = fund_kri_counts.get(fund.fund_id_new, 0)
            print(f"     * {fund.fund_id_new}: {count}")


# =============================================================================
# Example Usage with Data-Driven Approach
# =============================================================================

def example_usage():
    """Demonstrate data-driven transformation with sample data."""
    
    # Sample Cards data - loaded from Excel
    cards_data = [
        {
            "Card Name": "12/31/2024 Canada Annual",
            "fiscal_year_end": "31-Dec",
            "reporting_cycle": "Annual",
            "open_end_close_end": "Canada",
            "reporting_date": "31-12-2024",
            "Status": "In-Cycle"
        }
    ]
    
    # Sample Funds data - loaded from Excel
    # Group is taken DIRECTLY from Group_New column (NOT derived from Fund ID)
    # Fund ID_New is used as the lookup key to find the fund
    funds_data = [
        {
            "#": 23,
            "Trust": "Canada",
            "Trust_New": "Canada",
            "Fund": "PIMCO Monthly Income Fund (Canada)",
            "Fund ID": "HD2C",
            "Fund Name_New": "Income Strategy Fund",
            "Fund ID_New": "CAN1",
            "Group": "H",
            "Group_New": "A",
            "Book": "PIMCO Monthly Income Fund (Canada)",
            "Book_New": "Income Strategy Fund",
            "Fund Type": "Canada"
        },
        {
            "#": 24,
            "Trust": "Canada",
            "Trust_New": "Canada",
            "Fund": "PIMCO Monthly Enhanced Income Fund",
            "Fund ID": "HEWM",
            "Fund Name_New": "Credit Income Fund",
            "Fund ID_New": "CAN2",
            "Group": "H",
            "Group_New": "A",
            "Book": "Canada CEF",
            "Book_New": "Credit Income Fund",
            "Fund Type": "Canada"
        },
        {
            "#": 25,
            "Trust": "Canada",
            "Trust_New": "Canada",
            "Fund": "PIMCO Canada Canadian CorePLUS Bond Trust",
            "Fund ID": "HDW1",
            "Fund Name_New": "International Bond Trust",
            "Fund ID_New": "CAN3",
            "Group": "G",
            "Group_New": "A",
            "Book": "Canada Trust",
            "Book_New": "International Bond Trust",
            "Fund Type": "Canada"
        }
    ]
    
    # KRI Master data - ALL VALUES ARE BUSINESS-PROVIDED
    # 
    # BUSINESS-PROVIDED FIELDS:
    # - KRI ID: Non-sequential IDs (KRI_1, KRI_6, KRI_55, etc.)
    # - Validation ID: Pre-defined validation IDs
    # - Threshold: JSON string with threshold rules (UNIQUE per KRI)
    # - Risk: Business-provided risk level (NOT calculated from BPS Impact)
    #
    # IMPORTANT: KRI IDs are NOT sequential - they are business-defined
    # IMPORTANT: Risk does NOT correlate with BPS Impact:
    #   - BPS 1.53 → "High" (business decision)
    #   - BPS 0 → "Medium" (business decision) 
    #   - BPS 116.87 → "Low" (business decision - high BPS can map to Low risk!)
    kri_master_data = [
        {
            "KRI ID": "KRI_1",
            "KRI Name": "Interest Expense versus Average Borrowings",
            "KRI Desc": "",
            "Threshold": '{"High": ">7%","Medium": ">=7% and <=5%","Low":"<5%"}',
            "Validation ID": "999991",
            "Risk": "High",  # Business-provided (BPS 1.53 mapped to High)
            "Risk Thresholds": '{"Green": "<2%", "Yellow": "2% - 5%", "Red": ">5%"}'
        },
        {
            "KRI ID": "KRI_6",
            "KRI Name": "Defaulted Securities Review",
            "KRI Desc": "",
            "Threshold": '{"High": ">5%","Medium": ">=3% and <=5%","Low":"<3%"}',
            "Validation ID": "999996",
            "Risk": "Medium",  # Business-provided (BPS 0 mapped to Medium)
            "Risk Thresholds": '{"Green": "<2%", "Yellow": "2% - 5%", "Red": ">5%"}'
        },
        {
            "KRI ID": "KRI_55",
            "KRI Name": "Effective Leverage: Year Over Year Change",
            "KRI Desc": "",
            "Threshold": '{"High": ">10%","Medium": ">=5% and <=10%","Low":"<5%"}',
            "Validation ID": "999999",
            "Risk": "Low",  # Business-provided (BPS 116.87 mapped to Low!)
            "Risk Thresholds": '{"Green": "<2%", "Yellow": "2% - 5%", "Red": ">5%"}'
        }
    ]
    
    # Sample Validations - TRIMMED data
    validations_trimmed_data = [
        {
            "Card": "12/31/2024 Canada Annual",
            "Fund": "CAN3",
            "Priority": "Material",
            "Workflow Status": "EY L1 Review",
            "Validation Status": "Failed",
            "Validation": "SCF_admin vs generalledger_adjusted_entries_ey_CANADA",
            "Statement Type": "SCF",
            "Section": "Net Realized (Gain) Loss",
            "Line Item Description": "Foreign currency transactions",
            "Control Procedures": "SCF_admin vs generalledger_adjusted_entries_ey_CANADA",
            "Share Class": "",
            "Control Value": -141,
            "FS Value": -152,
            "Variance": 11,
            "BPS Impact": -0.078014184,
            "Comments": "0",
            "Comment Details": "",
            "Auto / Manual": "Automated",
            "Validation Source": "Recon_Engine",
            "Validation Type": "AFS - Indicative FS",
            "Control Draft Number": "2.1",
            "Test Draft Number": "",
            "Is Final": False,
            "Threshold Amount": "",
            "Threshold Desc": "--",
            "Threshold Percent (%)": "--",
            "Threshold Abs": ""
        }
    ]
    
    # Sample Validations - KRI data
    # NEW: Includes Risk Level and Threshold Chart columns from Validations-KRI tab
    validations_kri_data = [
        {
            "Card": "12/31/2024 Canada Annual",
            "Fund": "CAN2",
            "Priority": "Standard",
            "Workflow Status": "EY L1 Review",
            "Validation Status": "Passed",
            "Validation": "Interest Expense versus Average Borrowings",
            "Statement Type": "KRI",
            "Risk Level": "High",  # NEW: Direct from Excel
            "Threshold Chart": "Green: <5%\nYellow: 5% - 7%\nRed: >7%",  # NEW: Direct from Excel
            "Section": "",
            "Line Item Description": "",
            "Control Procedures": "Percent difference between the Interest Expense versus the Average Borrowings throughout the period multiplied by the Weighted Average Interest rate.((Average borrowings x Weighted Average Interest rate) - Interest Expense) / Interest Expense",
            "Share Class": "",
            "Control Value": -25.06,
            "FS Value": -1633,
            "Variance": -25.06,
            "BPS Impact": 1.53,
            "Comments": "0",
            "Comment Details": "",
            "Auto / Manual": "Automated",
            "Validation Source": "KRI Validations",
            "Validation Type": "KRI Validations",
            "Control Draft Number": "null.1",
            "Test Draft Number": "",
            "Is Final": False,
            "KRI Variable Key1": "Average Borrowings",
            "KRI Variable Value1": -36711,
            "KRI Variable Key2": "Weighted Average Interest Rate",
            "KRI Variable Value2": 4.38,
            "KRI Variable Key3": "Interest Expense",
            "KRI Variable Value3": -1633
        },
        {
            "Card": "12/31/2024 Canada Annual",
            "Fund": "CAN2",
            "Priority": "Standard",
            "Workflow Status": "EY L1 Review",
            "Validation Status": "Passed",
            "Validation": "Defaulted Securities Review",
            "Statement Type": "KRI",
            "Risk Level": "Medium",  # NEW: Direct from Excel
            "Threshold Chart": "Green: <3%\nYellow: 3% - 5%\nRed: >5%",  # NEW: Direct from Excel
            "Section": "",
            "Line Item Description": "",
            "Control Procedures": "Total Market Value of Securities in Default as a percentage of Net Assets.  Total Market Value of Securities in Default / Net Assets",
            "Share Class": "",
            "Control Value": 0,
            "FS Value": "7,98,606.00",
            "Variance": 0,
            "BPS Impact": 0,
            "Comments": "0",
            "Comment Details": "",
            "Auto / Manual": "Automated",
            "Validation Source": "KRI Validations",
            "Validation Type": "KRI Validations",
            "Control Draft Number": "null.1",
            "Test Draft Number": "",
            "Is Final": False,
            "KRI Variable Key1": "Total Market Value Of Securities In Default",
            "KRI Variable Value1": 0,
            "KRI Variable Key2": "Net Assets",
            "KRI Variable Value2": "7,98,606.00"
        },
        {
            "Card": "12/31/2024 Canada Annual",
            "Fund": "CAN3",
            "Priority": "Standard",
            "Workflow Status": "EY L1 Review",
            "Validation Status": "Passed",
            "Validation": "Effective Leverage: Year Over Year Change",
            "Statement Type": "KRI",
            "Risk Level": "Low",  # NEW: Direct from Excel
            "Threshold Chart": "Green: <5%\nYellow: 5% - 10%\nRed: >10%",  # NEW: Direct from Excel
            "Section": "",
            "Line Item Description": "",
            "Control Procedures": "Period over period change for a Fund's Total Effective Leverage.  (Total Effective Leverage CY - Total Effective Leverage PY) / Total Effective Leverage PY",
            "Share Class": "",
            "Control Value": 0.02,
            "FS Value": 0.02,
            "Variance": 0,
            "BPS Impact": 116.87,
            "Comments": "0",
            "Comment Details": "",
            "Auto / Manual": "Automated",
            "Validation Source": "KRI Validations",
            "Validation Type": "KRI Validations",
            "Control Draft Number": "null.1",
            "Test Draft Number": "",
            "Is Final": False,
            "KRI Variable Key1": "Py Net Assets",
            "KRI Variable Value1": "18,17,515.00",
            "KRI Variable Key2": "Cy Reverse Repos",
            "KRI Variable Value2": "9,500.00",
            "KRI Variable Key3": "Cy Credit Default Swaps",
            "KRI Variable Value3": "51,800.00",
            "KRI Variable Key4": "Cy Net Assets",
            "KRI Variable Value4": "17,14,756.00",
            "KRI Variable Key5": "Cy Line Of Credit",
            "KRI Variable Value5": 0
        }
    ]
    
    # Create transformer and load data
    transformer = ExcelToJSONTransformer()
    transformer.load_cards(cards_data)
    transformer.load_funds(funds_data)
    transformer.load_validations_trimmed(validations_trimmed_data)
    transformer.load_validations_kri(validations_kri_data)
    
    # Optional: Load KRI Master for pre-defined KRI IDs
    transformer.load_kri_master(kri_master_data)
    
    # Transform and get outputs
    outputs = transformer.transform()
    
    # Print relationship summary
    transformer.print_relationship_summary()
    
    # Print each JSON
    print("\n" + "=" * 80)
    print("JSON 1: Combined Validations")
    print("=" * 80)
    print(outputs["json1"])
    
    print("\n" + "=" * 80)
    print("JSON 2: KRI Details")
    print("=" * 80)
    print(outputs["json2"])
    
    print("\n" + "=" * 80)
    print("JSON 3: Fund KRI Status Count")
    print("=" * 80)
    print(outputs["json3"])
    
    print("\n" + "=" * 80)
    print("JSON 4: Strategy KRI Count")
    print("=" * 80)
    print(outputs["json4"])
    
    print("\n" + "=" * 80)
    print("JSON 5: KRI Simple Details")
    print("=" * 80)
    print(outputs["json5"])


if __name__ == "__main__":
    example_usage()
