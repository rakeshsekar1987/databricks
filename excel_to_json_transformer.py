#!/usr/bin/env python3
"""
Excel to JSON Transformation Framework - Data-Driven Version
Transforms 4+ Excel tabs into 5 JSON output files for KRI Validations system.

All mappings are derived from the input data - no hardcoding.
Supports multi-card processing with per-card output filtering.
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
    open_end_close_end: str  # This is the Trust/Region (Canada, America, India)
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
    """
    kri_id: str
    kri_name: str
    kri_desc: str
    threshold: str
    validation_id: str
    risk: str = ""
    risk_thresholds: str = ""


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
    row_index: int = 0
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
    # Remove Excel carriage return markers
    cleaned = str(text).replace('_x000D_', ' ')
    # Remove extra whitespace and newlines
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def clean_threshold_value(value: str) -> str:
    """Clean threshold values - convert '--' to empty string."""
    if not value or value == "--":
        return ""
    return str(value).strip()


def get_current_timestamp() -> str:
    """Get current timestamp in required format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


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
    """
    if not threshold_chart or not threshold_chart.strip():
        return ""
    
    result = {}
    
    # Clean the input - remove _x000D_ markers
    cleaned = threshold_chart.replace('_x000D_', '\n')
    
    # Split by newlines and process each line
    lines = cleaned.strip().split('\n')
    
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
        clean_text_val = re.sub(r'[^a-zA-Z0-9]', '', remaining)
        
        return f"{iso_date}{clean_text_val}{suffix}.json"
    else:
        # Fallback: just clean the card name
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', card_name)
        return f"{clean_name}{suffix}.json"


def get_output_file_names(card_name: str) -> Dict[str, str]:
    """
    Get all 5 output file names for a given card.
    
    File names are auto-generated from Card Name column in Cards tab.
    For each Card Name, 5 files are created with the card name as prefix/suffix.
    """
    base = generate_file_name_from_card(card_name, "")
    base_without_ext = base.replace(".json", "")
    
    return {
        "json1": f"{base_without_ext}.json",
        "json2": f"{base_without_ext}kri.json",
        "json3": f"{base_without_ext}kri-fund.json",
        "json4": f"{base_without_ext}strategy.json",
        "json5": f"{base_without_ext}kri-simple.json"
    }


def extract_trust_from_card(card: Card) -> str:
    """Extract the Trust/Region from a Card (from open_end_close_end field)."""
    return card.open_end_close_end if card else ""


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
        self._fund_order: Dict[str, int] = {}
        self._funds_by_trust: Dict[str, List[Fund]] = {}  # Trust -> List of Funds
        self._build_indexes()
    
    def _build_indexes(self):
        """Build lookup indexes dynamically from loaded data."""
        # Index funds
        for idx, fund in enumerate(self.funds):
            self._fund_index[fund.fund_id_new] = fund
            self._fund_index[fund.fund_id] = fund
            self._fund_order[fund.fund_id_new] = idx
            
            # Group funds by Trust_New
            trust = fund.trust_new
            if trust not in self._funds_by_trust:
                self._funds_by_trust[trust] = []
            self._funds_by_trust[trust].append(fund)
        
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
    
    def get_funds_by_trust(self, trust: str) -> List[Fund]:
        """Get all funds for a specific Trust."""
        return self._funds_by_trust.get(trust, [])
    
    def get_fund_group(self, fund_code: str) -> str:
        """Get the group for a fund - DIRECTLY from Group_New column."""
        fund = self.get_fund(fund_code)
        if fund:
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
# Global KRI Mapping Service - Consistent IDs Across All Cards
# =============================================================================

class GlobalKRIMappingService:
    """
    Service for mapping KRI validation names to KRI IDs globally.
    Ensures same KRI Name gets same KRI ID regardless of which card it appears in.
    """
    
    def __init__(self, all_kri_validations: List[Validation]):
        self._kri_id_map: Dict[str, str] = {}  # name -> kri_id
        self._validation_id_map: Dict[str, str] = {}  # name -> validation_id
        self._kri_order: List[str] = []  # Track order of unique KRIs globally
        
        # Register all KRIs from all validations to establish global order
        for v in all_kri_validations:
            if v.validation not in self._kri_order:
                self._kri_order.append(v.validation)
        
        # Generate consistent IDs based on global order
        for idx, kri_name in enumerate(self._kri_order):
            self._kri_id_map[kri_name] = f"KRI_{idx + 1}"
            self._validation_id_map[kri_name] = str(999990 + idx + 1)
    
    def get_kri_id(self, validation_name: str) -> str:
        """Get globally consistent KRI ID for a validation name."""
        return self._kri_id_map.get(validation_name, "")
    
    def get_validation_id(self, validation_name: str) -> str:
        """Get globally consistent validation ID for a KRI."""
        return self._validation_id_map.get(validation_name, "")
    
    def get_all_kri_names(self) -> List[str]:
        """Get all registered KRI names in global order."""
        return self._kri_order.copy()
    
    def get_total_kri_count(self) -> int:
        """Get total number of unique KRIs globally."""
        return len(self._kri_order)


# =============================================================================
# Validation ID Service - Sequential IDs for TRIMMED validations
# =============================================================================

class ValidationIDService:
    """
    Service for generating sequential validation IDs for TRIMMED validations.
    """
    
    def __init__(self, start_id: int = 1000):
        self._counter = start_id
        self._id_cache: Dict[str, str] = {}
    
    def get_validation_id(self, validation: Validation) -> str:
        """Generate sequential ID for a TRIMMED validation."""
        cache_key = f"{validation.card}|{validation.fund}|{validation.validation}"
        if cache_key in self._id_cache:
            return self._id_cache[cache_key]
        
        self._counter += 1
        val_id = str(self._counter)
        self._id_cache[cache_key] = val_id
        return val_id


# =============================================================================
# JSON Builders - Per-Card Filtering
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
    Builder for JSON 1: Combined Validations for a specific card.
    """
    
    def __init__(self, validations: List[Validation], 
                 lookup_service: DataLookupService,
                 global_kri_mapping: GlobalKRIMappingService,
                 validation_id_service: ValidationIDService):
        self.validations = validations
        self.lookup = lookup_service
        self.global_kri_mapping = global_kri_mapping
        self.val_id_service = validation_id_service
    
    def _generate_record_id(self, validation: Validation, index: int) -> str:
        """Generate unique record ID based on validation data."""
        seed = f"{validation.card}|{validation.fund}|{validation.validation}|{index}"
        return generate_unique_id(seed)
    
    def _build_validation_object(self, validation: Validation, index: int) -> Dict[str, Any]:
        """Build a single validation object."""
        
        # Cross-referenced from Funds tab
        trust = self.lookup.get_trust(validation.fund)
        book = self.lookup.get_book(validation.fund)
        group = self.lookup.get_fund_group(validation.fund)
        
        # Generate IDs
        record_id = self._generate_record_id(validation, index)
        
        # Get validation ID
        if validation.is_kri:
            validation_id = self.global_kri_mapping.get_validation_id(validation.validation)
        else:
            validation_id = self.val_id_service.get_validation_id(validation)
        
        # Extract draft number
        control_draft = extract_draft_number(validation.control_draft_number)
        
        # Build validation description
        if validation.is_kri and validation.control_procedures:
            validation_desc = clean_text(validation.control_procedures)
        else:
            validation_desc = validation.validation
        
        # Build valuesUsedInFormula
        values_in_formula = ""
        if validation.is_kri and validation.kri_variables:
            values_in_formula = build_values_used_in_formula(validation.kri_variables)
        
        return {
            "id": record_id,
            "validationId": validation_id,
            "auditVersionControlDs": "1",
            "writeTs": get_current_timestamp(),
            "trust": trust,
            "group": group,
            "book": book,
            "fundCode": validation.fund,
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
            "priority": validation.priority,
            "validationStatus": validation.validation_status,
            "isFinalDraft": False,  # Boolean, not empty string
            "lineItemDescription": validation.line_item_description or "",
            "statementType": validation.statement_type,
            "testDraftNumber": validation.test_draft_number or "",
            "thresholdColAmount": clean_threshold_value(validation.threshold_amount),
            "thresholdColDesc": clean_threshold_value(validation.threshold_desc),
            "thresholdPercent": clean_threshold_value(validation.threshold_percent),
            "thresholdAbs": clean_threshold_value(validation.threshold_abs),
            "validationDesc": validation_desc,
            "webappWorkflowStatus": validation.workflow_status,
            "valuesUsedInFormula": values_in_formula,
            "isCpoControl": "0",
            "isCpoTest": "0",
            "isBannerLessControl": "0",
            "isBannerLessTest": "0",
            "isBlueFontControl": "0",
            "isBlueFontTest": "0",
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
                    "rowCount": len(validation_objects),
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
    Builder for JSON 2: KRI Details grouped by KRI type for a specific card.
    """
    
    def __init__(self, kri_validations: List[Validation],
                 lookup_service: DataLookupService,
                 global_kri_mapping: GlobalKRIMappingService):
        self.kri_validations = kri_validations
        self.lookup = lookup_service
        self.global_kri_mapping = global_kri_mapping
    
    def build(self) -> Dict[str, Any]:
        # Group validations by KRI name
        kri_groups: OrderedDict[str, List[Validation]] = OrderedDict()
        for v in self.kri_validations:
            if v.validation not in kri_groups:
                kri_groups[v.validation] = []
            kri_groups[v.validation].append(v)
        
        kri_details = []
        
        for kri_name, validations in kri_groups.items():
            first_val = validations[0]
            
            # Get globally consistent KRI ID
            kri_id = self.global_kri_mapping.get_kri_id(kri_name)
            
            # Get description from Control Procedures
            kri_desc = clean_text(first_val.control_procedures)
            
            # Transform threshold chart to JSON
            threshold_chart = first_val.threshold_chart if first_val.threshold_chart else ""
            threshold = transform_threshold_chart_to_json(threshold_chart)
            
            fund_details = []
            for v in validations:
                fund_name = self.lookup.get_book(v.fund)
                bps = parse_number(v.bps_impact) or 0
                
                # Risk from Excel column
                risk = v.risk_level if v.risk_level else ""
                
                # Validation ID
                val_id = self.global_kri_mapping.get_validation_id(v.validation)
                
                values_formula = build_values_used_in_formula(v.kri_variables)
                
                fund_details.append({
                    "risk": risk,
                    "threshold": None,
                    "fundName": fund_name,
                    "fundCode": v.fund,
                    "result": str(bps),
                    "strategy": "Credit - Diversified Income",
                    "validationStatus": v.validation_status,
                    "validationId": val_id,
                    "valuesUsedInFormula": values_formula
                })
            
            kri_details.append({
                "kriName": kri_name,
                "kriId": kri_id,
                "kriDesc": kri_desc,
                "threshold": threshold,
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


class JSON3Builder(BaseJSONBuilder):
    """
    Builder for JSON 3: Fund KRI Status Count for a specific card.
    Only includes funds belonging to the same Trust as the card.
    """
    
    def __init__(self, kri_validations: List[Validation],
                 card_funds: List[Fund],
                 global_kri_mapping: GlobalKRIMappingService):
        self.kri_validations = kri_validations
        self.card_funds = card_funds
        self.global_kri_mapping = global_kri_mapping
    
    def build(self) -> Dict[str, Any]:
        # Get unique KRIs for this card
        unique_kris_in_card = list(OrderedDict.fromkeys(v.validation for v in self.kri_validations))
        kri_total_count = str(len(unique_kris_in_card))
        
        # Count KRIs per fund
        fund_kri_counts: Dict[str, int] = {}
        for v in self.kri_validations:
            fund_kri_counts[v.fund] = fund_kri_counts.get(v.fund, 0) + 1
        
        # Build fund status count only for funds belonging to this card's Trust
        fund_status_counts = []
        for fund in self.card_funds:
            fund_code = fund.fund_id_new
            fund_name = fund.fund_name_new
            kri_count = fund_kri_counts.get(fund_code, 0)
            
            fund_status_counts.append({
                "kriTotalCount": kri_total_count,
                "kriStatusCount": str(kri_count),
                "analyticsStatus": "High",
                "fundCode": fund_code,
                "fundName": fund_name
            })
        
        # Build KRI filter list only for KRIs present in this card
        kri_filter = []
        for kri_name in unique_kris_in_card:
            kri_id = self.global_kri_mapping.get_kri_id(kri_name)
            val_id = self.global_kri_mapping.get_validation_id(kri_name)
            
            kri_filter.append({
                "kriId": kri_id,
                "kriName": kri_name,
                "validationId": val_id
            })
        
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
    Builder for JSON 4: Strategy KRI Count for a specific card.
    """
    
    def __init__(self, kri_validations: List[Validation]):
        self.kri_validations = kri_validations
    
    def build(self) -> Dict[str, Any]:
        # Count unique KRI types in this card
        unique_kris = set(v.validation for v in self.kri_validations)
        kri_total_count = str(len(unique_kris))
        
        # Total KRI validations in this card
        kri_status_count = str(len(self.kri_validations))
        
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
    Builder for JSON 5: Simple KRI Details list for a specific card.
    Only includes KRIs that appear in this card.
    """
    
    def __init__(self, kri_validations: List[Validation],
                 global_kri_mapping: GlobalKRIMappingService):
        self.kri_validations = kri_validations
        self.global_kri_mapping = global_kri_mapping
    
    def build(self) -> Dict[str, Any]:
        # Get unique KRIs in order encountered in this card
        unique_kris = list(OrderedDict.fromkeys(v.validation for v in self.kri_validations))
        
        kri_details = []
        for kri_name in unique_kris:
            kri_id = self.global_kri_mapping.get_kri_id(kri_name)
            val_id = self.global_kri_mapping.get_validation_id(kri_name)
            
            kri_details.append({
                "kriId": kri_id,
                "kriName": kri_name,
                "validationId": val_id
            })
        
        return {
            "kriDetails": kri_details
        }


# =============================================================================
# Main Transformer Class - Multi-Card Support
# =============================================================================

class ExcelToJSONTransformer:
    """
    Main transformer class that orchestrates the conversion.
    Supports multi-card processing with per-card output filtering.
    """
    
    def __init__(self):
        self.cards: List[Card] = []
        self.funds: List[Fund] = []
        self.validations_trimmed: List[Validation] = []
        self.validations_kri: List[Validation] = []
        self.kri_master: List[KRIMaster] = []
        
        # Services - initialized after data loading
        self.lookup_service: Optional[DataLookupService] = None
        self.global_kri_mapping: Optional[GlobalKRIMappingService] = None
        self.validation_id_service: Optional[ValidationIDService] = None
    
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
        """Load KRI Master data (optional)."""
        for row in kri_master_data:
            self.kri_master.append(KRIMaster(
                kri_id=row.get('KRI ID', ''),
                kri_name=row.get('KRI Name', ''),
                kri_desc=row.get('KRI Desc', ''),
                threshold=row.get('Threshold', ''),
                validation_id=row.get('Validation ID', ''),
                risk=row.get('Risk', ''),
                risk_thresholds=row.get('Risk Thresholds', '')
            ))
    
    def _parse_validation(self, row: Dict[str, Any], is_kri: bool, row_index: int) -> Validation:
        """Parse a validation row from Excel data."""
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
            risk_level=row.get('Risk Level', ''),
            threshold_chart=row.get('Threshold Chart', ''),
            kri_id=row.get('KRI ID', ''),
            validation_id_from_excel=row.get('Validation ID', '')
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
        self.lookup_service = DataLookupService(self.funds, self.cards)
        
        # Global KRI mapping - ensures consistent IDs across all cards
        self.global_kri_mapping = GlobalKRIMappingService(self.validations_kri)
        
        # Validation ID service for TRIMMED validations
        self.validation_id_service = ValidationIDService()
    
    def get_card_names(self) -> List[str]:
        """Get all card names."""
        return [card.card_name for card in self.cards]
    
    def transform_for_card(self, card_name: str) -> Dict[str, str]:
        """
        Transform data for a specific card.
        Filters validations and funds to only include data for this card.
        """
        # Initialize services if not already done
        if not self.lookup_service:
            self._initialize_services()
        
        # Get the card
        card = self.lookup_service.get_card(card_name)
        if not card:
            return {}
        
        # Get the Trust/Region for this card
        card_trust = extract_trust_from_card(card)
        
        # Filter validations for this card
        card_validations_trimmed = [v for v in self.validations_trimmed if v.card == card_name]
        card_validations_kri = [v for v in self.validations_kri if v.card == card_name]
        
        # Get funds for this card's Trust
        card_funds = self.lookup_service.get_funds_by_trust(card_trust)
        
        # Combine validations
        all_validations = card_validations_trimmed + card_validations_kri
        
        # Build all JSONs for this card
        json1_builder = JSON1Builder(
            all_validations, 
            self.lookup_service, 
            self.global_kri_mapping,
            self.validation_id_service
        )
        json2_builder = JSON2Builder(
            card_validations_kri, 
            self.lookup_service, 
            self.global_kri_mapping
        )
        json3_builder = JSON3Builder(
            card_validations_kri, 
            card_funds,
            self.global_kri_mapping
        )
        json4_builder = JSON4Builder(card_validations_kri)
        json5_builder = JSON5Builder(
            card_validations_kri, 
            self.global_kri_mapping
        )
        
        return {
            "json1": json1_builder.to_json(),
            "json2": json2_builder.to_json(),
            "json3": json3_builder.to_json(),
            "json4": json4_builder.to_json(),
            "json5": json5_builder.to_json()
        }
    
    def transform_all_cards(self) -> Dict[str, Dict[str, str]]:
        """
        Transform data for all cards.
        Returns a dictionary with card names as keys and output dictionaries as values.
        """
        self._initialize_services()
        
        results = {}
        for card in self.cards:
            card_name = card.card_name
            results[card_name] = self.transform_for_card(card_name)
        
        return results
    
    def transform(self) -> Dict[str, str]:
        """
        Transform all loaded data into 5 JSON outputs.
        For backward compatibility - uses first card only.
        """
        if self.cards:
            return self.transform_for_card(self.cards[0].card_name)
        return {}
    
    def get_file_names(self, card_name: str = None) -> Dict[str, str]:
        """Get output file names based on Card Name."""
        if card_name is None and self.cards:
            card_name = self.cards[0].card_name
        return get_output_file_names(card_name or "")


# =============================================================================
# Example Usage
# =============================================================================

def example_usage():
    """Demonstrate multi-card transformation with sample data."""
    
    # Sample Cards data
    cards_data = [
        {
            "Card Name": "12/31/2024 Canada Annual",
            "fiscal_year_end": "31-Dec",
            "reporting_cycle": "Annual",
            "open_end_close_end": "Canada",
            "reporting_date": "31-12-2024",
            "Status": "In-Cycle"
        },
        {
            "Card Name": "12/31/2025 America Annual",
            "fiscal_year_end": "31-Dec",
            "reporting_cycle": "Annual",
            "open_end_close_end": "America",
            "reporting_date": "31-12-2025",
            "Status": "In-Cycle"
        }
    ]
    
    # Sample Funds data
    funds_data = [
        {"#": 23, "Trust": "Canada", "Trust_New": "Canada", "Fund ID_New": "CAN1", 
         "Fund Name_New": "Income Strategy Fund", "Group_New": "A", "Book_New": "Income Strategy Fund"},
        {"#": 24, "Trust": "Canada", "Trust_New": "Canada", "Fund ID_New": "CAN2", 
         "Fund Name_New": "Credit Income Fund", "Group_New": "A", "Book_New": "Credit Income Fund"},
        {"#": 25, "Trust": "Canada", "Trust_New": "Canada", "Fund ID_New": "CAN3", 
         "Fund Name_New": "International Bond Trust", "Group_New": "A", "Book_New": "International Bond Trust"},
        {"#": 26, "Trust": "America", "Trust_New": "America", "Fund ID_New": "AM1", 
         "Fund Name_New": "Income Strategy Fund", "Group_New": "A", "Book_New": "Income Strategy Fund"},
        {"#": 27, "Trust": "America", "Trust_New": "America", "Fund ID_New": "AM2", 
         "Fund Name_New": "Credit Income Fund", "Group_New": "B", "Book_New": "Credit Income Fund"},
        {"#": 28, "Trust": "America", "Trust_New": "America", "Fund ID_New": "AM3", 
         "Fund Name_New": "International Bond Trust", "Group_New": "C", "Book_New": "International Bond Trust"}
    ]
    
    # Sample KRI Validations
    validations_kri_data = [
        {"Card": "12/31/2024 Canada Annual", "Fund": "CAN2", "Validation": "Interest Expense versus Average Borrowings",
         "Statement Type": "KRI", "Risk Level": "High", "Threshold Chart": "Green: <5%\nYellow: 5% - 7%\nRed: >7%",
         "Priority": "Standard", "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Control Procedures": "Test control procedure", "BPS Impact": 1.53, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations"},
        {"Card": "12/31/2024 Canada Annual", "Fund": "CAN2", "Validation": "Defaulted Securities Review",
         "Statement Type": "KRI", "Risk Level": "Medium", "Threshold Chart": "Green: <3%\nYellow: 3% - 5%\nRed: >5%",
         "Priority": "Standard", "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Control Procedures": "Test control procedure", "BPS Impact": 0, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations"},
        {"Card": "12/31/2025 America Annual", "Fund": "AM2", "Validation": "Interest Expense versus Average Borrowings",
         "Statement Type": "KRI", "Risk Level": "High", "Threshold Chart": "Green: <5%\nYellow: 5% - 7%\nRed: >7%",
         "Priority": "Standard", "Workflow Status": "EY L1 Review", "Validation Status": "Failed",
         "Control Procedures": "Test control procedure", "BPS Impact": 1.53, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations"}
    ]
    
    # Create transformer and load data
    transformer = ExcelToJSONTransformer()
    transformer.load_cards(cards_data)
    transformer.load_funds(funds_data)
    transformer.load_validations_kri(validations_kri_data)
    
    # Transform all cards
    all_outputs = transformer.transform_all_cards()
    
    for card_name, outputs in all_outputs.items():
        print(f"\n{'='*80}")
        print(f"Card: {card_name}")
        print(f"{'='*80}")
        file_names = get_output_file_names(card_name)
        for key in ['json1', 'json2', 'json3', 'json4', 'json5']:
            print(f"\n{file_names[key]}:")
            print(outputs[key][:500] + "..." if len(outputs[key]) > 500 else outputs[key])


if __name__ == "__main__":
    example_usage()
