#!/usr/bin/env python3
"""
Excel to JSON Transformation Framework
Transforms 4 Excel tabs into 5 JSON output files for KRI Validations system.
"""

import json
import hashlib
import uuid
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


# =============================================================================
# Configuration
# =============================================================================

class Config:
    """Configuration for KRI ID mappings and default values."""
    
    # KRI Name to KRI ID mapping
    KRI_MAPPINGS = {
        "Interest Expense versus Average Borrowings": "KRI_1",
        "Defaulted Securities Review": "KRI_6",
        "Effective Leverage: Year Over Year Change": "KRI_9A",
    }
    
    # Validation ID base for KRI validations
    KRI_VALIDATION_ID_BASE = 999990
    
    # Default values
    DEFAULT_ANALYTICS_STATUS = "High"
    DEFAULT_STRATEGY = "Credit - Diversified Income"
    DEFAULT_RISK = "Low"
    DEFAULT_THRESHOLD = '{"High": ">30%","Medium": ">=15% and <30%","Low":"<15%"}'
    DEFAULT_AUDIT_VERSION = "1"
    
    # Group mapping (can be extended based on business logic)
    GROUP_MAPPINGS = {
        "CAN1": "A",
        "CAN2": "B", 
        "CAN3": "C",
    }


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
    group_new: str
    book: str
    book_new: str
    fund_type: str
    card_mappings: Dict[str, bool] = field(default_factory=dict)


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


# =============================================================================
# Utility Functions
# =============================================================================

def generate_request_id() -> str:
    """Generate a UUID-based request ID (uppercase, no hyphens)."""
    return uuid.uuid4().hex.upper()


def generate_validation_id(prefix: str = "") -> str:
    """Generate a unique validation ID hash."""
    random_part = uuid.uuid4().hex
    hash_input = f"{prefix}{random_part}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:64]


def generate_short_id(prefix: str, index: int) -> str:
    """Generate a short unique ID with prefix pattern."""
    base = f"{index}{prefix}5fd44acd764fe393ec848fbfcb3ca6e27aa319df7245fa83b597e466cc75be"
    return base[:64]


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


def build_values_used_in_formula(kri_variables: Dict[str, Any]) -> str:
    """Build the valuesUsedInFormula JSON string from KRI variables."""
    if not kri_variables:
        return ""
    
    # Convert values to numbers
    result = {}
    for key, value in kri_variables.items():
        if key and key != "" and key != "--":
            parsed = parse_number(value)
            if parsed is not None:
                result[key] = parsed
    
    if not result:
        return ""
    
    return json.dumps(result)


def extract_draft_number(value: str) -> Optional[str]:
    """Extract draft number from value like '2.1' -> '2'."""
    if not value or value == "null.1" or value == "null":
        return None
    # Extract the integer part
    match = re.match(r'(\d+)', str(value))
    if match:
        return match.group(1)
    return None


# =============================================================================
# Data Lookup Service
# =============================================================================

class DataLookupService:
    """Service for cross-referencing data between Excel tabs."""
    
    def __init__(self, funds: List[Fund], cards: List[Card]):
        self.funds = funds
        self.cards = cards
        self._fund_index: Dict[str, Fund] = {}
        self._card_index: Dict[str, Card] = {}
        self._build_indexes()
    
    def _build_indexes(self):
        """Build lookup indexes for efficient cross-referencing."""
        for fund in self.funds:
            # Index by Fund ID_New (e.g., CAN1, CAN2)
            self._fund_index[fund.fund_id_new] = fund
            # Also index by Fund ID for flexibility
            self._fund_index[fund.fund_id] = fund
        
        for card in self.cards:
            self._card_index[card.card_name] = card
    
    def get_fund(self, fund_code: str) -> Optional[Fund]:
        """Get fund details by fund code."""
        return self._fund_index.get(fund_code)
    
    def get_card(self, card_name: str) -> Optional[Card]:
        """Get card details by card name."""
        return self._card_index.get(card_name)
    
    def get_all_funds(self) -> List[Fund]:
        """Get all funds."""
        return self.funds
    
    def get_mapped_group(self, fund_code: str) -> str:
        """Get the mapped group letter for a fund code."""
        return Config.GROUP_MAPPINGS.get(fund_code, "A")


# =============================================================================
# KRI ID Mapping Service
# =============================================================================

class KRIMappingService:
    """Service for mapping KRI validation names to KRI IDs."""
    
    def __init__(self):
        self._kri_id_counter = 0
        self._validation_id_map: Dict[str, str] = {}
        self._kri_id_map: Dict[str, str] = {}
    
    def get_kri_id(self, validation_name: str) -> str:
        """Get KRI ID for a validation name."""
        if validation_name in self._kri_id_map:
            return self._kri_id_map[validation_name]
        
        # Check configured mappings first
        if validation_name in Config.KRI_MAPPINGS:
            kri_id = Config.KRI_MAPPINGS[validation_name]
            self._kri_id_map[validation_name] = kri_id
            return kri_id
        
        # Generate new KRI ID
        self._kri_id_counter += 1
        kri_id = f"KRI_{self._kri_id_counter}"
        self._kri_id_map[validation_name] = kri_id
        return kri_id
    
    def get_validation_id(self, validation_name: str, index: int) -> str:
        """Get or generate validation ID for a KRI validation."""
        if validation_name in self._validation_id_map:
            return self._validation_id_map[validation_name]
        
        # Generate based on KRI ID pattern
        kri_id = self.get_kri_id(validation_name)
        # Extract number from KRI ID
        match = re.search(r'(\d+)', kri_id)
        if match:
            base_num = int(match.group(1))
            val_id = str(Config.KRI_VALIDATION_ID_BASE + base_num)
        else:
            val_id = str(Config.KRI_VALIDATION_ID_BASE + index + 1)
        
        self._validation_id_map[validation_name] = val_id
        return val_id
    
    def get_all_kri_mappings(self) -> Dict[str, str]:
        """Get all KRI name to ID mappings."""
        return self._kri_id_map.copy()


# =============================================================================
# JSON Builders
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
    """Builder for JSON 1: Combined Validations."""
    
    def __init__(self, validations: List[Validation], 
                 lookup_service: DataLookupService,
                 kri_mapping_service: KRIMappingService):
        self.validations = validations
        self.lookup = lookup_service
        self.kri_mapping = kri_mapping_service
        self._validation_counter = 1160
        self._kri_counter = 0
    
    def _build_validation_object(self, validation: Validation, index: int) -> Dict[str, Any]:
        """Build a single validation object for the JSON output."""
        fund = self.lookup.get_fund(validation.fund)
        
        # Generate ID
        prefix = ["9s", "0t", "1u", "2v"][index % 4]
        id_value = generate_short_id(prefix, index)
        
        # Get validation ID
        if validation.is_kri:
            self._kri_counter += 1
            validation_id = self.kri_mapping.get_validation_id(validation.validation, self._kri_counter)
        else:
            self._validation_counter += 1
            validation_id = str(self._validation_counter)
        
        # Get fund-related fields
        trust = fund.trust_new if fund else "Unknown"
        group = self.lookup.get_mapped_group(validation.fund)
        book = fund.book_new if fund else ""
        
        # Build values used in formula for KRI
        values_in_formula = ""
        if validation.is_kri and validation.kri_variables:
            values_in_formula = build_values_used_in_formula(validation.kri_variables)
        
        # Extract control draft number
        control_draft = extract_draft_number(validation.control_draft_number)
        
        # Build validation description
        if validation.is_kri:
            validation_desc = clean_text(validation.control_procedures)
        else:
            validation_desc = validation.validation
        
        return {
            "id": id_value,
            "trust": trust,
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
            "fundCode": validation.fund,
            "group": group,
            "book": book,
            "priority": validation.priority,
            "validationStatus": validation.validation_status,
            "auditVersionControlDs": Config.DEFAULT_AUDIT_VERSION,
            "writeTs": get_current_timestamp(),
            "isFinalDraft": validation.is_final,
            "validationId": validation_id,
            "lineItemDescription": validation.line_item_description or "",
            "statementType": validation.statement_type,
            "testDraftNumber": validation.test_draft_number or "",
            "isCpoControl": "0",
            "isCpoTest": "0",
            "isBannerLessControl": "0",
            "isBannerLessTest": "0",
            "isBlueFontControl": "0",
            "isBlueFontTest": "0",
            "thresholdColAmount": validation.threshold_amount or "",
            "thresholdColDesc": validation.threshold_desc or "",
            "thresholdPercent": validation.threshold_percent or "",
            "thresholdAbs": validation.threshold_abs or "",
            "validationDesc": validation_desc,
            "webappWorkflowStatus": validation.workflow_status,
            "valuesUsedInFormula": values_in_formula,
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
    """Builder for JSON 2: KRI Details grouped by KRI type."""
    
    def __init__(self, kri_validations: List[Validation],
                 lookup_service: DataLookupService,
                 kri_mapping_service: KRIMappingService):
        self.kri_validations = kri_validations
        self.lookup = lookup_service
        self.kri_mapping = kri_mapping_service
    
    def _calculate_risk(self, bps_impact: float) -> str:
        """Calculate risk level based on BPS impact."""
        bps = abs(bps_impact) if bps_impact else 0
        if bps >= 30:
            return "High"
        elif bps >= 15:
            return "Medium"
        else:
            return "Low"
    
    def build(self) -> Dict[str, Any]:
        # Group validations by KRI name
        kri_groups: Dict[str, List[Validation]] = {}
        for v in self.kri_validations:
            if v.validation not in kri_groups:
                kri_groups[v.validation] = []
            kri_groups[v.validation].append(v)
        
        kri_details = []
        kri_counter = 0
        
        for kri_name, validations in kri_groups.items():
            kri_id = self.kri_mapping.get_kri_id(kri_name)
            
            # Get description from first validation
            kri_desc = clean_text(validations[0].control_procedures)
            
            fund_details = []
            for v in validations:
                kri_counter += 1
                fund = self.lookup.get_fund(v.fund)
                validation_id = self.kri_mapping.get_validation_id(kri_name, kri_counter)
                
                bps = parse_number(v.bps_impact) or 0
                values_formula = build_values_used_in_formula(v.kri_variables)
                
                fund_details.append({
                    "risk": self._calculate_risk(bps),
                    "threshold": None,
                    "fundName": fund.book_new if fund else v.fund,
                    "fundCode": v.fund,
                    "result": str(bps),
                    "strategy": Config.DEFAULT_STRATEGY,
                    "validationStatus": v.validation_status,
                    "validationId": validation_id,
                    "valuesUsedInFormula": values_formula
                })
            
            kri_details.append({
                "kriName": kri_name,
                "kriId": kri_id,
                "kriDesc": kri_desc,
                "threshold": Config.DEFAULT_THRESHOLD,
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
    """Builder for JSON 3: Fund KRI Status Count."""
    
    def __init__(self, kri_validations: List[Validation],
                 lookup_service: DataLookupService,
                 kri_mapping_service: KRIMappingService):
        self.kri_validations = kri_validations
        self.lookup = lookup_service
        self.kri_mapping = kri_mapping_service
    
    def build(self) -> Dict[str, Any]:
        # Count unique KRI types
        unique_kris = set(v.validation for v in self.kri_validations)
        kri_total_count = str(len(unique_kris))
        
        # Count KRIs per fund
        fund_kri_counts: Dict[str, int] = {}
        for v in self.kri_validations:
            fund_kri_counts[v.fund] = fund_kri_counts.get(v.fund, 0) + 1
        
        # Build fund status count for ALL funds
        fund_status_counts = []
        for fund in self.lookup.get_all_funds():
            fund_code = fund.fund_id_new
            kri_count = fund_kri_counts.get(fund_code, 0)
            
            fund_status_counts.append({
                "kriTotalCount": kri_total_count,
                "kriStatusCount": str(kri_count),
                "analyticsStatus": Config.DEFAULT_ANALYTICS_STATUS,
                "fundCode": fund_code,
                "fundName": fund.fund_name_new
            })
        
        # Build KRI filter list
        kri_filter = []
        kri_counter = 0
        for kri_name in unique_kris:
            kri_counter += 1
            kri_filter.append({
                "kriId": self.kri_mapping.get_kri_id(kri_name),
                "kriName": kri_name,
                "validationId": self.kri_mapping.get_validation_id(kri_name, kri_counter)
            })
        
        # Build status filter
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
    """Builder for JSON 4: Strategy KRI Count."""
    
    def __init__(self, kri_validations: List[Validation]):
        self.kri_validations = kri_validations
    
    def build(self) -> Dict[str, Any]:
        # Count unique KRI types
        unique_kris = set(v.validation for v in self.kri_validations)
        kri_total_count = str(len(unique_kris))
        
        # Total KRI validations
        kri_status_count = str(len(self.kri_validations))
        
        return {
            "requestDetails": {
                "requestId": generate_request_id()
            },
            "data": [
                {
                    "kriTotalCount": kri_total_count,
                    "kriStatusCount": kri_status_count,
                    "analyticsStatus": Config.DEFAULT_ANALYTICS_STATUS,
                    "strategy": Config.DEFAULT_STRATEGY
                }
            ]
        }


class JSON5Builder(BaseJSONBuilder):
    """Builder for JSON 5: Simple KRI Details list."""
    
    def __init__(self, kri_validations: List[Validation],
                 kri_mapping_service: KRIMappingService):
        self.kri_validations = kri_validations
        self.kri_mapping = kri_mapping_service
    
    def build(self) -> Dict[str, Any]:
        # Get unique KRIs
        unique_kris = set(v.validation for v in self.kri_validations)
        
        kri_details = []
        kri_counter = 0
        for kri_name in unique_kris:
            kri_counter += 1
            kri_details.append({
                "kriId": self.kri_mapping.get_kri_id(kri_name),
                "kriName": kri_name,
                "validationId": self.kri_mapping.get_validation_id(kri_name, kri_counter)
            })
        
        return {
            "kriDetails": kri_details
        }


# =============================================================================
# Main Transformer Class
# =============================================================================

class ExcelToJSONTransformer:
    """Main transformer class that orchestrates the conversion."""
    
    def __init__(self):
        self.cards: List[Card] = []
        self.funds: List[Fund] = []
        self.validations_trimmed: List[Validation] = []
        self.validations_kri: List[Validation] = []
        self.lookup_service: Optional[DataLookupService] = None
        self.kri_mapping_service = KRIMappingService()
    
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
    
    def _parse_validation(self, row: Dict[str, Any], is_kri: bool) -> Validation:
        """Parse a validation row from Excel data."""
        # Extract KRI variables for KRI validations
        kri_variables = {}
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
            is_kri=is_kri
        )
    
    def load_validations_trimmed(self, validations_data: List[Dict[str, Any]]):
        """Load validations from TRIMMED tab."""
        for row in validations_data:
            self.validations_trimmed.append(self._parse_validation(row, is_kri=False))
    
    def load_validations_kri(self, validations_data: List[Dict[str, Any]]):
        """Load validations from KRI tab."""
        for row in validations_data:
            self.validations_kri.append(self._parse_validation(row, is_kri=True))
    
    def transform(self) -> Dict[str, str]:
        """
        Transform all loaded data into 5 JSON outputs.
        Returns a dictionary with keys json1-json5 and JSON string values.
        """
        # Initialize lookup service
        self.lookup_service = DataLookupService(self.funds, self.cards)
        
        # Combine validations for JSON 1
        all_validations = self.validations_trimmed + self.validations_kri
        
        # Build all JSONs
        json1_builder = JSON1Builder(all_validations, self.lookup_service, self.kri_mapping_service)
        json2_builder = JSON2Builder(self.validations_kri, self.lookup_service, self.kri_mapping_service)
        json3_builder = JSON3Builder(self.validations_kri, self.lookup_service, self.kri_mapping_service)
        json4_builder = JSON4Builder(self.validations_kri)
        json5_builder = JSON5Builder(self.validations_kri, self.kri_mapping_service)
        
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


# =============================================================================
# Example Usage / Test
# =============================================================================

def example_usage():
    """Demonstrate usage with sample data matching the provided Excel."""
    
    # Sample Cards data
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
    
    # Sample Funds data
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
    validations_kri_data = [
        {
            "Card": "12/31/2024 Canada Annual",
            "Fund": "CAN2",
            "Priority": "Standard",
            "Workflow Status": "EY L1 Review",
            "Validation Status": "Passed",
            "Validation": "Interest Expense versus Average Borrowings",
            "Statement Type": "KRI",
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
    
    # Transform and get outputs
    outputs = transformer.transform()
    
    # Print each JSON
    print("=" * 80)
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
