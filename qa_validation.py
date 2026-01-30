#!/usr/bin/env python3
"""
Comprehensive QA Validation for Excel to JSON Transformation Framework
Tests every field mapping, calculation, and cross-reference against expected output.
"""

import json
import sys
from typing import Dict, List, Any, Tuple
from excel_to_json_transformer import (
    ExcelToJSONTransformer, 
    parse_number, 
    extract_numeric_suffix, 
    number_to_letter,
    extract_draft_number,
    clean_text,
    build_values_used_in_formula
)
from collections import OrderedDict


class QAValidator:
    """Comprehensive QA Validator for the transformation framework."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.transformer = None
        self.outputs = {}
    
    def assert_equal(self, actual, expected, field_name: str, context: str = ""):
        """Assert two values are equal and track results."""
        # Handle numeric comparisons with tolerance
        if isinstance(expected, float) and isinstance(actual, float):
            if abs(actual - expected) < 0.0001:
                self.passed += 1
                return True
        
        if actual == expected:
            self.passed += 1
            return True
        else:
            self.failed += 1
            error_msg = f"FAIL: {field_name}"
            if context:
                error_msg = f"FAIL: [{context}] {field_name}"
            error_msg += f"\n       Expected: {repr(expected)}\n       Actual:   {repr(actual)}"
            self.errors.append(error_msg)
            print(error_msg)
            return False
    
    def assert_in(self, actual, expected_list: List, field_name: str, context: str = ""):
        """Assert value is in expected list."""
        if actual in expected_list:
            self.passed += 1
            return True
        else:
            self.failed += 1
            error_msg = f"FAIL: [{context}] {field_name} - {repr(actual)} not in {expected_list}"
            self.errors.append(error_msg)
            print(error_msg)
            return False
    
    def assert_not_none(self, actual, field_name: str, context: str = ""):
        """Assert value is not None."""
        if actual is not None:
            self.passed += 1
            return True
        else:
            self.failed += 1
            error_msg = f"FAIL: [{context}] {field_name} is None"
            self.errors.append(error_msg)
            print(error_msg)
            return False
    
    def assert_type(self, actual, expected_type, field_name: str, context: str = ""):
        """Assert value is of expected type."""
        if isinstance(actual, expected_type):
            self.passed += 1
            return True
        else:
            self.failed += 1
            error_msg = f"FAIL: [{context}] {field_name} type is {type(actual).__name__}, expected {expected_type.__name__}"
            self.errors.append(error_msg)
            print(error_msg)
            return False

    def setup(self):
        """Set up the transformer with test data."""
        print("=" * 80)
        print("SETTING UP TEST DATA")
        print("=" * 80)
        
        self.transformer = ExcelToJSONTransformer()
        
        # Load Cards
        self.transformer.load_cards([{
            'Card Name': '12/31/2024 Canada Annual',
            'fiscal_year_end': '31-Dec',
            'reporting_cycle': 'Annual',
            'open_end_close_end': 'Canada',
            'reporting_date': '31-12-2024',
            'Status': 'In-Cycle'
        }])
        
        # Load Funds - Group_New is used directly for the group field
        # (Not derived from Fund ID_New suffix)
        self.transformer.load_funds([
            {'#': 23, 'Trust': 'Canada', 'Trust_New': 'Canada', 
             'Fund': 'PIMCO Monthly Income Fund (Canada)', 'Fund ID': 'HD2C', 
             'Fund Name_New': 'Income Strategy Fund', 'Fund ID_New': 'CAN1',
             'Group': 'H', 'Group_New': 'A',  # Group_New = A
             'Book': 'PIMCO Monthly Income Fund (Canada)', 'Book_New': 'Income Strategy Fund', 
             'Fund Type': 'Canada'},
            {'#': 24, 'Trust': 'Canada', 'Trust_New': 'Canada', 
             'Fund': 'PIMCO Monthly Enhanced Income Fund', 'Fund ID': 'HEWM', 
             'Fund Name_New': 'Credit Income Fund', 'Fund ID_New': 'CAN2',
             'Group': 'H', 'Group_New': 'B',  # Group_New = B (business-provided)
             'Book': 'Canada CEF', 'Book_New': 'Credit Income Fund', 
             'Fund Type': 'Canada'},
            {'#': 25, 'Trust': 'Canada', 'Trust_New': 'Canada', 
             'Fund': 'PIMCO Canada Canadian CorePLUS Bond Trust', 'Fund ID': 'HDW1', 
             'Fund Name_New': 'International Bond Trust', 'Fund ID_New': 'CAN3',
             'Group': 'G', 'Group_New': 'C',  # Group_New = C (business-provided)
             'Book': 'Canada Trust', 'Book_New': 'International Bond Trust', 
             'Fund Type': 'Canada'}
        ])
        
        # Load KRI Master - Risk is business-provided, NOT calculated from BPS
        self.transformer.load_kri_master([
            {'KRI ID': 'KRI_1', 'KRI Name': 'Interest Expense versus Average Borrowings', 
             'KRI Desc': '', 'Threshold': '{"High": ">30%","Medium": ">=15% and <30%","Low":"<15%"}', 
             'Validation ID': '999991',
             'Risk': 'Medium',  # Business-provided (not calculated from BPS 1.53)
             'Risk Thresholds': '{"Green": "<2%", "Yellow": "2% - 5%", "Red": ">5%"}'},
            {'KRI ID': 'KRI_6', 'KRI Name': 'Defaulted Securities Review', 
             'KRI Desc': '', 'Threshold': '{"High": ">30%","Medium": ">=15% and <30%","Low":"<15%"}', 
             'Validation ID': '999996',
             'Risk': 'Medium',  # Business-provided (BPS 0 mapped to Medium by business)
             'Risk Thresholds': '{"Green": "<2%", "Yellow": "2% - 5%", "Red": ">5%"}'},
            {'KRI ID': 'KRI_9A', 'KRI Name': 'Effective Leverage: Year Over Year Change', 
             'KRI Desc': '', 'Threshold': '{"High": ">30%","Medium": ">=15% and <30%","Low":"<15%"}', 
             'Validation ID': '999999',
             'Risk': 'High',  # Business-provided
             'Risk Thresholds': '{"Green": "<2%", "Yellow": "2% - 5%", "Red": ">5%"}'}
        ])
        
        # Load Validations - TRIMMED
        self.transformer.load_validations_trimmed([{
            'Card': '12/31/2024 Canada Annual', 'Fund': 'CAN3', 'Priority': 'Material',
            'Workflow Status': 'EY L1 Review', 'Validation Status': 'Failed',
            'Validation': 'SCF_admin vs generalledger_adjusted_entries_ey_CANADA',
            'Statement Type': 'SCF', 'Section': 'Net Realized (Gain) Loss',
            'Line Item Description': 'Foreign currency transactions',
            'Control Procedures': 'SCF_admin vs generalledger_adjusted_entries_ey_CANADA',
            'Share Class': '', 'Control Value': -141, 'FS Value': -152,
            'Variance': 11, 'BPS Impact': -0.078014184, 'Auto / Manual': 'Automated',
            'Validation Source': 'Recon_Engine', 'Validation Type': 'AFS - Indicative FS',
            'Control Draft Number': '2.1', 'Test Draft Number': '', 'Is Final': False,
            'Threshold Amount': '', 'Threshold Desc': '--', 'Threshold Percent (%)': '--', 'Threshold Abs': ''
        }])
        
        # Load Validations - KRI
        self.transformer.load_validations_kri([
            {'Card': '12/31/2024 Canada Annual', 'Fund': 'CAN2', 'Priority': 'Standard',
             'Workflow Status': 'EY L1 Review', 'Validation Status': 'Passed',
             'Validation': 'Interest Expense versus Average Borrowings', 'Statement Type': 'KRI',
             'Section': '', 'Line Item Description': '',
             'Control Procedures': 'Percent difference between the Interest Expense versus the Average Borrowings throughout the period multiplied by the Weighted Average Interest rate.((Average borrowings x Weighted Average Interest rate) - Interest Expense) / Interest Expense',
             'Share Class': '', 'Control Value': -25.06, 'FS Value': -1633, 'Variance': -25.06, 'BPS Impact': 1.53,
             'Auto / Manual': 'Automated', 'Validation Source': 'KRI Validations', 'Validation Type': 'KRI Validations',
             'Control Draft Number': 'null.1', 'Test Draft Number': '', 'Is Final': False,
             'KRI Variable Key1': 'Average Borrowings', 'KRI Variable Value1': -36711,
             'KRI Variable Key2': 'Weighted Average Interest Rate', 'KRI Variable Value2': 4.38,
             'KRI Variable Key3': 'Interest Expense', 'KRI Variable Value3': -1633},
            {'Card': '12/31/2024 Canada Annual', 'Fund': 'CAN2', 'Priority': 'Standard',
             'Workflow Status': 'EY L1 Review', 'Validation Status': 'Passed',
             'Validation': 'Defaulted Securities Review', 'Statement Type': 'KRI',
             'Section': '', 'Line Item Description': '',
             'Control Procedures': 'Total Market Value of Securities in Default as a percentage of Net Assets. Total Market Value of Securities in Default / Net Assets',
             'Share Class': '', 'Control Value': 0, 'FS Value': '7,98,606.00', 'Variance': 0, 'BPS Impact': 0,
             'Auto / Manual': 'Automated', 'Validation Source': 'KRI Validations', 'Validation Type': 'KRI Validations',
             'Control Draft Number': 'null.1', 'Test Draft Number': '', 'Is Final': False,
             'KRI Variable Key1': 'Total Market Value Of Securities In Default', 'KRI Variable Value1': 0,
             'KRI Variable Key2': 'Net Assets', 'KRI Variable Value2': '7,98,606.00'},
            {'Card': '12/31/2024 Canada Annual', 'Fund': 'CAN3', 'Priority': 'Standard',
             'Workflow Status': 'EY L1 Review', 'Validation Status': 'Passed',
             'Validation': 'Effective Leverage: Year Over Year Change', 'Statement Type': 'KRI',
             'Section': '', 'Line Item Description': '',
             'Control Procedures': 'Period over period change for a Fund Total Effective Leverage. (Total Effective Leverage CY - Total Effective Leverage PY) / Total Effective Leverage PY',
             'Share Class': '', 'Control Value': 0.02, 'FS Value': 0.02, 'Variance': 0, 'BPS Impact': 116.87,
             'Auto / Manual': 'Automated', 'Validation Source': 'KRI Validations', 'Validation Type': 'KRI Validations',
             'Control Draft Number': 'null.1', 'Test Draft Number': '', 'Is Final': False,
             'KRI Variable Key1': 'Py Net Assets', 'KRI Variable Value1': '18,17,515.00',
             'KRI Variable Key2': 'Cy Reverse Repos', 'KRI Variable Value2': '9,500.00',
             'KRI Variable Key3': 'Cy Credit Default Swaps', 'KRI Variable Value3': '51,800.00',
             'KRI Variable Key4': 'Cy Net Assets', 'KRI Variable Value4': '17,14,756.00',
             'KRI Variable Key5': 'Cy Line Of Credit', 'KRI Variable Value5': 0}
        ])
        
        # Transform
        raw_outputs = self.transformer.transform()
        self.outputs = {
            'json1': json.loads(raw_outputs['json1']),
            'json2': json.loads(raw_outputs['json2']),
            'json3': json.loads(raw_outputs['json3']),
            'json4': json.loads(raw_outputs['json4']),
            'json5': json.loads(raw_outputs['json5'])
        }
        
        print("Test data loaded and transformed successfully.\n")

    def test_utility_functions(self):
        """Test utility functions."""
        print("=" * 80)
        print("TEST 1: UTILITY FUNCTIONS")
        print("=" * 80)
        
        # Test extract_numeric_suffix
        self.assert_equal(extract_numeric_suffix('CAN1'), ('CAN', 1), 'extract_numeric_suffix(CAN1)')
        self.assert_equal(extract_numeric_suffix('CAN2'), ('CAN', 2), 'extract_numeric_suffix(CAN2)')
        self.assert_equal(extract_numeric_suffix('CAN3'), ('CAN', 3), 'extract_numeric_suffix(CAN3)')
        self.assert_equal(extract_numeric_suffix('FUND10'), ('FUND', 10), 'extract_numeric_suffix(FUND10)')
        self.assert_equal(extract_numeric_suffix('ABC'), ('ABC', 0), 'extract_numeric_suffix(ABC) - no number')
        
        # Test number_to_letter
        self.assert_equal(number_to_letter(1), 'A', 'number_to_letter(1)')
        self.assert_equal(number_to_letter(2), 'B', 'number_to_letter(2)')
        self.assert_equal(number_to_letter(3), 'C', 'number_to_letter(3)')
        self.assert_equal(number_to_letter(26), 'Z', 'number_to_letter(26)')
        self.assert_equal(number_to_letter(0), 'A', 'number_to_letter(0) - fallback')
        
        # Test parse_number
        self.assert_equal(parse_number(-141), -141.0, 'parse_number(-141)')
        self.assert_equal(parse_number('7,98,606.00'), 798606.0, 'parse_number(7,98,606.00)')
        self.assert_equal(parse_number('18,17,515.00'), 1817515.0, 'parse_number(18,17,515.00)')
        self.assert_equal(parse_number('9,500.00'), 9500.0, 'parse_number(9,500.00)')
        self.assert_equal(parse_number(''), None, 'parse_number(empty)')
        self.assert_equal(parse_number('--'), None, 'parse_number(--)')
        self.assert_equal(parse_number(None), None, 'parse_number(None)')
        
        # Test extract_draft_number
        self.assert_equal(extract_draft_number('2.1'), '2', 'extract_draft_number(2.1)')
        self.assert_equal(extract_draft_number('null.1'), None, 'extract_draft_number(null.1)')
        self.assert_equal(extract_draft_number('null'), None, 'extract_draft_number(null)')
        self.assert_equal(extract_draft_number(''), None, 'extract_draft_number(empty)')
        self.assert_equal(extract_draft_number('10.5'), '10', 'extract_draft_number(10.5)')
        
        # Test clean_text
        self.assert_equal(clean_text('Hello  World'), 'Hello World', 'clean_text removes extra spaces')
        self.assert_equal(clean_text('Line1\nLine2'), 'Line1 Line2', 'clean_text removes newlines')
        self.assert_equal(clean_text(''), '', 'clean_text empty string')
        
        # Test build_values_used_in_formula
        test_vars = OrderedDict([('Key1', 100), ('Key2', 200)])
        result = build_values_used_in_formula(test_vars)
        self.assert_equal(json.loads(result), {'Key1': 100.0, 'Key2': 200.0}, 'build_values_used_in_formula')
        
        empty_result = build_values_used_in_formula({})
        self.assert_equal(empty_result, '', 'build_values_used_in_formula empty')
        
        print()

    def test_json1_structure(self):
        """Test JSON 1 structure."""
        print("=" * 80)
        print("TEST 2: JSON 1 STRUCTURE")
        print("=" * 80)
        
        json1 = self.outputs['json1']
        
        # Test top-level structure
        self.assert_not_none(json1.get('requestDetails'), 'requestDetails', 'JSON1')
        self.assert_not_none(json1.get('data'), 'data', 'JSON1')
        self.assert_not_none(json1['requestDetails'].get('requestId'), 'requestId', 'JSON1')
        self.assert_type(json1['requestDetails']['requestId'], str, 'requestId type', 'JSON1')
        
        # Test getValidations structure
        get_validations = json1['data'].get('getValidations')
        self.assert_not_none(get_validations, 'getValidations', 'JSON1')
        self.assert_equal(get_validations.get('rowCount'), 4, 'rowCount', 'JSON1')
        self.assert_equal(get_validations['pageInfo']['hasNextPage'], False, 'hasNextPage', 'JSON1')
        self.assert_equal(get_validations['pageInfo']['hasPreviousPage'], False, 'hasPreviousPage', 'JSON1')
        
        # Test validations array
        validations = get_validations.get('validations')
        self.assert_not_none(validations, 'validations array', 'JSON1')
        self.assert_equal(len(validations), 4, 'validations count', 'JSON1')
        
        print()

    def test_json1_validation1_trimmed(self):
        """Test JSON 1 Validation 1 (TRIMMED - CAN3)."""
        print("=" * 80)
        print("TEST 3: JSON 1 - VALIDATION 1 (TRIMMED - CAN3)")
        print("=" * 80)
        
        v = self.outputs['json1']['data']['getValidations']['validations'][0]
        ctx = 'JSON1-V1'
        
        # Cross-referenced fields from Funds tab
        self.assert_equal(v['trust'], 'Canada', 'trust (from Trust_New)', ctx)
        self.assert_equal(v['group'], 'C', 'group (from Group_New for CAN3)', ctx)
        self.assert_equal(v['book'], 'International Bond Trust', 'book (from Book_New)', ctx)
        
        # Direct from Validations Excel
        self.assert_equal(v['fund'], 'CAN3', 'fund', ctx)
        self.assert_equal(v['fundCode'], 'CAN3', 'fundCode', ctx)
        self.assert_equal(v['shareClass'], '', 'shareClass', ctx)
        self.assert_equal(v['section'], 'Net Realized (Gain) Loss', 'section', ctx)
        self.assert_equal(v['validation'], 'SCF_admin vs generalledger_adjusted_entries_ey_CANADA', 'validation', ctx)
        self.assert_equal(v['controlValue'], -141.0, 'controlValue', ctx)
        self.assert_equal(v['fsValue'], -152.0, 'fsValue', ctx)
        self.assert_equal(v['variance'], 11.0, 'variance', ctx)
        self.assert_equal(v['bpsImpact'], -0.078014184, 'bpsImpact', ctx)
        self.assert_equal(v['validationType'], 'AFS - Indicative FS', 'validationType', ctx)
        self.assert_equal(v['validationSource'], 'Recon_Engine', 'validationSource', ctx)
        self.assert_equal(v['controlDraftNumber'], '2', 'controlDraftNumber (extracted from 2.1)', ctx)
        self.assert_equal(v['autoManual'], 'Automated', 'autoManual', ctx)
        self.assert_equal(v['priority'], 'Material', 'priority', ctx)
        self.assert_equal(v['validationStatus'], 'Failed', 'validationStatus', ctx)
        self.assert_equal(v['isFinalDraft'], False, 'isFinalDraft', ctx)
        self.assert_equal(v['lineItemDescription'], 'Foreign currency transactions', 'lineItemDescription', ctx)
        self.assert_equal(v['statementType'], 'SCF', 'statementType', ctx)
        self.assert_equal(v['testDraftNumber'], '', 'testDraftNumber', ctx)
        self.assert_equal(v['thresholdColDesc'], '--', 'thresholdColDesc', ctx)
        self.assert_equal(v['thresholdPercent'], '--', 'thresholdPercent', ctx)
        
        # Derived fields
        self.assert_equal(v['validationDesc'], 'SCF_admin vs generalledger_adjusted_entries_ey_CANADA', 
                         'validationDesc (for non-KRI uses Validation)', ctx)
        self.assert_equal(v['webappWorkflowStatus'], 'EY L1 Review', 'webappWorkflowStatus', ctx)
        self.assert_equal(v['valuesUsedInFormula'], '', 'valuesUsedInFormula (empty for non-KRI)', ctx)
        
        # Default fields
        self.assert_equal(v['auditVersionControlDs'], '1', 'auditVersionControlDs', ctx)
        self.assert_equal(v['isCpoControl'], '0', 'isCpoControl', ctx)
        self.assert_equal(v['isCpoTest'], '0', 'isCpoTest', ctx)
        self.assert_equal(v['isBannerLessControl'], '0', 'isBannerLessControl', ctx)
        self.assert_equal(v['isBannerLessTest'], '0', 'isBannerLessTest', ctx)
        self.assert_equal(v['isBlueFontControl'], '0', 'isBlueFontControl', ctx)
        self.assert_equal(v['isBlueFontTest'], '0', 'isBlueFontTest', ctx)
        
        # Null fields
        self.assert_equal(v['analyticStatus'], None, 'analyticStatus', ctx)
        self.assert_equal(v['fundStrategy'], None, 'fundStrategy', ctx)
        self.assert_equal(v['result'], None, 'result', ctx)
        self.assert_equal(v['threshold'], None, 'threshold', ctx)
        
        # Generated fields
        self.assert_not_none(v['id'], 'id', ctx)
        self.assert_not_none(v['validationId'], 'validationId', ctx)
        self.assert_not_none(v['writeTs'], 'writeTs', ctx)
        
        print()

    def test_json1_validation2_kri(self):
        """Test JSON 1 Validation 2 (KRI - CAN2 - Interest Expense)."""
        print("=" * 80)
        print("TEST 4: JSON 1 - VALIDATION 2 (KRI - CAN2 - Interest Expense)")
        print("=" * 80)
        
        v = self.outputs['json1']['data']['getValidations']['validations'][1]
        ctx = 'JSON1-V2'
        
        # Cross-referenced fields
        self.assert_equal(v['trust'], 'Canada', 'trust', ctx)
        self.assert_equal(v['group'], 'B', 'group (from Group_New for CAN2)', ctx)
        self.assert_equal(v['book'], 'Credit Income Fund', 'book', ctx)
        
        # Direct from Excel
        self.assert_equal(v['fund'], 'CAN2', 'fund', ctx)
        self.assert_equal(v['validation'], 'Interest Expense versus Average Borrowings', 'validation', ctx)
        self.assert_equal(v['controlValue'], -25.06, 'controlValue', ctx)
        self.assert_equal(v['fsValue'], -1633.0, 'fsValue', ctx)
        self.assert_equal(v['variance'], -25.06, 'variance', ctx)
        self.assert_equal(v['bpsImpact'], 1.53, 'bpsImpact', ctx)
        self.assert_equal(v['validationType'], 'KRI Validations', 'validationType', ctx)
        self.assert_equal(v['validationSource'], 'KRI Validations', 'validationSource', ctx)
        self.assert_equal(v['controlDraftNumber'], None, 'controlDraftNumber (null.1→None)', ctx)
        self.assert_equal(v['priority'], 'Standard', 'priority', ctx)
        self.assert_equal(v['validationStatus'], 'Passed', 'validationStatus', ctx)
        self.assert_equal(v['statementType'], 'KRI', 'statementType', ctx)
        
        # KRI-specific fields
        self.assert_equal(v['validationId'], '999991', 'validationId (from KRI Master)', ctx)
        
        # validationDesc should be from Control Procedures for KRI
        self.assert_in('Percent difference', v['validationDesc'], 'validationDesc contains expected text', ctx)
        
        # valuesUsedInFormula
        formula = json.loads(v['valuesUsedInFormula'])
        self.assert_equal(formula.get('Average Borrowings'), -36711.0, 'valuesUsedInFormula.Average Borrowings', ctx)
        self.assert_equal(formula.get('Weighted Average Interest Rate'), 4.38, 'valuesUsedInFormula.Weighted Average Interest Rate', ctx)
        self.assert_equal(formula.get('Interest Expense'), -1633.0, 'valuesUsedInFormula.Interest Expense', ctx)
        
        print()

    def test_json1_validation3_kri(self):
        """Test JSON 1 Validation 3 (KRI - CAN2 - Defaulted Securities)."""
        print("=" * 80)
        print("TEST 5: JSON 1 - VALIDATION 3 (KRI - CAN2 - Defaulted Securities)")
        print("=" * 80)
        
        v = self.outputs['json1']['data']['getValidations']['validations'][2]
        ctx = 'JSON1-V3'
        
        self.assert_equal(v['fund'], 'CAN2', 'fund', ctx)
        self.assert_equal(v['group'], 'B', 'group', ctx)
        self.assert_equal(v['book'], 'Credit Income Fund', 'book', ctx)
        self.assert_equal(v['validation'], 'Defaulted Securities Review', 'validation', ctx)
        self.assert_equal(v['fsValue'], 798606.0, 'fsValue (parsed from 7,98,606.00)', ctx)
        self.assert_equal(v['bpsImpact'], 0.0, 'bpsImpact', ctx)
        self.assert_equal(v['validationId'], '999996', 'validationId (KRI_6)', ctx)
        
        # valuesUsedInFormula
        formula = json.loads(v['valuesUsedInFormula'])
        self.assert_equal(formula.get('Total Market Value Of Securities In Default'), 0.0, 
                         'valuesUsedInFormula.Total Market Value', ctx)
        self.assert_equal(formula.get('Net Assets'), 798606.0, 'valuesUsedInFormula.Net Assets', ctx)
        
        print()

    def test_json1_validation4_kri(self):
        """Test JSON 1 Validation 4 (KRI - CAN3 - Effective Leverage)."""
        print("=" * 80)
        print("TEST 6: JSON 1 - VALIDATION 4 (KRI - CAN3 - Effective Leverage)")
        print("=" * 80)
        
        v = self.outputs['json1']['data']['getValidations']['validations'][3]
        ctx = 'JSON1-V4'
        
        self.assert_equal(v['fund'], 'CAN3', 'fund', ctx)
        self.assert_equal(v['group'], 'C', 'group (from Group_New for CAN3)', ctx)
        self.assert_equal(v['book'], 'International Bond Trust', 'book', ctx)
        self.assert_equal(v['validation'], 'Effective Leverage: Year Over Year Change', 'validation', ctx)
        self.assert_equal(v['controlValue'], 0.02, 'controlValue', ctx)
        self.assert_equal(v['fsValue'], 0.02, 'fsValue', ctx)
        self.assert_equal(v['bpsImpact'], 116.87, 'bpsImpact', ctx)
        self.assert_equal(v['priority'], 'Standard', 'priority (from Excel)', ctx)
        self.assert_equal(v['validationId'], '999999', 'validationId (KRI_9A)', ctx)
        
        # valuesUsedInFormula
        formula = json.loads(v['valuesUsedInFormula'])
        self.assert_equal(formula.get('Py Net Assets'), 1817515.0, 'valuesUsedInFormula.Py Net Assets', ctx)
        self.assert_equal(formula.get('Cy Reverse Repos'), 9500.0, 'valuesUsedInFormula.Cy Reverse Repos', ctx)
        self.assert_equal(formula.get('Cy Credit Default Swaps'), 51800.0, 'valuesUsedInFormula.Cy Credit Default Swaps', ctx)
        self.assert_equal(formula.get('Cy Net Assets'), 1714756.0, 'valuesUsedInFormula.Cy Net Assets', ctx)
        self.assert_equal(formula.get('Cy Line Of Credit'), 0.0, 'valuesUsedInFormula.Cy Line Of Credit', ctx)
        
        print()

    def test_json2_structure_and_content(self):
        """Test JSON 2 structure and content."""
        print("=" * 80)
        print("TEST 7: JSON 2 - KRI DETAILS")
        print("=" * 80)
        
        json2 = self.outputs['json2']
        ctx = 'JSON2'
        
        # Structure
        self.assert_not_none(json2.get('requestDetails'), 'requestDetails', ctx)
        self.assert_not_none(json2.get('data'), 'data', ctx)
        
        kri_details = json2['data'].get('kriDetails')
        self.assert_not_none(kri_details, 'kriDetails', ctx)
        self.assert_equal(len(kri_details), 3, 'kriDetails count (3 unique KRIs)', ctx)
        
        # KRI 1: Interest Expense
        kri1 = kri_details[0]
        self.assert_equal(kri1['kriName'], 'Interest Expense versus Average Borrowings', 'kri1.kriName', ctx)
        self.assert_equal(kri1['kriId'], 'KRI_1', 'kri1.kriId', ctx)
        self.assert_in('Percent difference', kri1['kriDesc'], 'kri1.kriDesc', ctx)
        self.assert_not_none(kri1['threshold'], 'kri1.threshold', ctx)
        
        # KRI 1 fundDetails
        fd1 = kri1['fundDetails'][0]
        self.assert_equal(fd1['fundCode'], 'CAN2', 'kri1.fundDetails[0].fundCode', ctx)
        self.assert_equal(fd1['fundName'], 'Credit Income Fund', 'kri1.fundDetails[0].fundName (from Book_New)', ctx)
        self.assert_equal(fd1['validationStatus'], 'Passed', 'kri1.fundDetails[0].validationStatus', ctx)
        self.assert_equal(fd1['validationId'], '999991', 'kri1.fundDetails[0].validationId', ctx)
        self.assert_equal(fd1['risk'], 'Medium', 'kri1.fundDetails[0].risk (business-provided from KRI Master)', ctx)
        self.assert_equal(fd1['result'], '1.53', 'kri1.fundDetails[0].result', ctx)
        
        # KRI 2: Defaulted Securities
        kri2 = kri_details[1]
        self.assert_equal(kri2['kriName'], 'Defaulted Securities Review', 'kri2.kriName', ctx)
        self.assert_equal(kri2['kriId'], 'KRI_6', 'kri2.kriId', ctx)
        
        fd2 = kri2['fundDetails'][0]
        self.assert_equal(fd2['fundCode'], 'CAN2', 'kri2.fundDetails[0].fundCode', ctx)
        self.assert_equal(fd2['fundName'], 'Credit Income Fund', 'kri2.fundDetails[0].fundName', ctx)
        self.assert_equal(fd2['risk'], 'Medium', 'kri2.fundDetails[0].risk (business-provided: BPS 0 mapped to Medium)', ctx)
        self.assert_equal(fd2['validationId'], '999996', 'kri2.fundDetails[0].validationId', ctx)
        
        # KRI 3: Effective Leverage
        kri3 = kri_details[2]
        self.assert_equal(kri3['kriName'], 'Effective Leverage: Year Over Year Change', 'kri3.kriName', ctx)
        self.assert_equal(kri3['kriId'], 'KRI_9A', 'kri3.kriId', ctx)
        
        fd3 = kri3['fundDetails'][0]
        self.assert_equal(fd3['fundCode'], 'CAN3', 'kri3.fundDetails[0].fundCode', ctx)
        self.assert_equal(fd3['fundName'], 'International Bond Trust', 'kri3.fundDetails[0].fundName (from Book_New)', ctx)
        self.assert_equal(fd3['risk'], 'High', 'kri3.fundDetails[0].risk (business-provided from KRI Master)', ctx)
        self.assert_equal(fd3['validationId'], '999999', 'kri3.fundDetails[0].validationId', ctx)
        
        print()

    def test_json3_structure_and_content(self):
        """Test JSON 3 structure and content."""
        print("=" * 80)
        print("TEST 8: JSON 3 - FUND KRI STATUS COUNT")
        print("=" * 80)
        
        json3 = self.outputs['json3']
        ctx = 'JSON3'
        
        # Structure
        self.assert_not_none(json3.get('requestDetails'), 'requestDetails', ctx)
        self.assert_not_none(json3.get('data'), 'data', ctx)
        
        # fundKriStatusCount
        fund_counts = json3['data'].get('fundKriStatusCount')
        self.assert_not_none(fund_counts, 'fundKriStatusCount', ctx)
        self.assert_equal(len(fund_counts), 3, 'fundKriStatusCount length (3 funds)', ctx)
        
        # CAN1
        f1 = fund_counts[0]
        self.assert_equal(f1['fundCode'], 'CAN1', 'fund1.fundCode', ctx)
        self.assert_equal(f1['fundName'], 'Income Strategy Fund', 'fund1.fundName (from Fund Name_New)', ctx)
        self.assert_equal(f1['kriTotalCount'], '3', 'fund1.kriTotalCount', ctx)
        self.assert_equal(f1['kriStatusCount'], '0', 'fund1.kriStatusCount (no KRIs for CAN1)', ctx)
        self.assert_equal(f1['analyticsStatus'], 'High', 'fund1.analyticsStatus', ctx)
        
        # CAN2
        f2 = fund_counts[1]
        self.assert_equal(f2['fundCode'], 'CAN2', 'fund2.fundCode', ctx)
        self.assert_equal(f2['fundName'], 'Credit Income Fund', 'fund2.fundName (from Fund Name_New)', ctx)
        self.assert_equal(f2['kriTotalCount'], '3', 'fund2.kriTotalCount', ctx)
        self.assert_equal(f2['kriStatusCount'], '2', 'fund2.kriStatusCount (2 KRIs for CAN2)', ctx)
        
        # CAN3
        f3 = fund_counts[2]
        self.assert_equal(f3['fundCode'], 'CAN3', 'fund3.fundCode', ctx)
        self.assert_equal(f3['fundName'], 'International Bond Trust', 'fund3.fundName (from Fund Name_New)', ctx)
        self.assert_equal(f3['kriTotalCount'], '3', 'fund3.kriTotalCount', ctx)
        self.assert_equal(f3['kriStatusCount'], '1', 'fund3.kriStatusCount (1 KRI for CAN3)', ctx)
        
        # kriFilter
        kri_filter = json3['data'].get('kriFilter')
        self.assert_not_none(kri_filter, 'kriFilter', ctx)
        self.assert_equal(len(kri_filter), 3, 'kriFilter length', ctx)
        
        # Verify KRI filter entries
        kri_names = [k['kriName'] for k in kri_filter]
        self.assert_in('Interest Expense versus Average Borrowings', kri_names, 'kriFilter contains Interest Expense', ctx)
        self.assert_in('Defaulted Securities Review', kri_names, 'kriFilter contains Defaulted Securities', ctx)
        self.assert_in('Effective Leverage: Year Over Year Change', kri_names, 'kriFilter contains Effective Leverage', ctx)
        
        # statusFilter
        status_filter = json3['data'].get('statusFilter')
        self.assert_not_none(status_filter, 'statusFilter', ctx)
        self.assert_in('Low', status_filter, 'statusFilter contains Low', ctx)
        self.assert_in('High', status_filter, 'statusFilter contains High', ctx)
        
        print()

    def test_json4_structure_and_content(self):
        """Test JSON 4 structure and content."""
        print("=" * 80)
        print("TEST 9: JSON 4 - STRATEGY KRI COUNT")
        print("=" * 80)
        
        json4 = self.outputs['json4']
        ctx = 'JSON4'
        
        # Structure
        self.assert_not_none(json4.get('requestDetails'), 'requestDetails', ctx)
        self.assert_not_none(json4.get('data'), 'data', ctx)
        self.assert_type(json4['data'], list, 'data type', ctx)
        self.assert_equal(len(json4['data']), 1, 'data length', ctx)
        
        # Content
        d = json4['data'][0]
        self.assert_equal(d['kriTotalCount'], '3', 'kriTotalCount (distinct KRIs)', ctx)
        self.assert_equal(d['kriStatusCount'], '3', 'kriStatusCount (all KRI validations)', ctx)
        self.assert_equal(d['analyticsStatus'], 'High', 'analyticsStatus', ctx)
        self.assert_equal(d['strategy'], 'Credit - Diversified Income', 'strategy', ctx)
        
        print()

    def test_json5_structure_and_content(self):
        """Test JSON 5 structure and content."""
        print("=" * 80)
        print("TEST 10: JSON 5 - KRI SIMPLE DETAILS")
        print("=" * 80)
        
        json5 = self.outputs['json5']
        ctx = 'JSON5'
        
        # Structure
        self.assert_not_none(json5.get('kriDetails'), 'kriDetails', ctx)
        self.assert_equal(len(json5['kriDetails']), 3, 'kriDetails length', ctx)
        
        # Verify each KRI
        kri_map = {k['kriName']: k for k in json5['kriDetails']}
        
        # Interest Expense
        k1 = kri_map.get('Interest Expense versus Average Borrowings')
        self.assert_not_none(k1, 'Interest Expense entry exists', ctx)
        if k1:
            self.assert_equal(k1['kriId'], 'KRI_1', 'Interest Expense kriId', ctx)
            self.assert_equal(k1['validationId'], '999991', 'Interest Expense validationId', ctx)
        
        # Defaulted Securities
        k2 = kri_map.get('Defaulted Securities Review')
        self.assert_not_none(k2, 'Defaulted Securities entry exists', ctx)
        if k2:
            self.assert_equal(k2['kriId'], 'KRI_6', 'Defaulted Securities kriId', ctx)
            self.assert_equal(k2['validationId'], '999996', 'Defaulted Securities validationId', ctx)
        
        # Effective Leverage
        k3 = kri_map.get('Effective Leverage: Year Over Year Change')
        self.assert_not_none(k3, 'Effective Leverage entry exists', ctx)
        if k3:
            self.assert_equal(k3['kriId'], 'KRI_9A', 'Effective Leverage kriId', ctx)
            self.assert_equal(k3['validationId'], '999999', 'Effective Leverage validationId', ctx)
        
        print()

    def test_id_consistency_across_jsons(self):
        """Test that IDs are consistent across all JSON outputs."""
        print("=" * 80)
        print("TEST 11: ID CONSISTENCY ACROSS JSONS")
        print("=" * 80)
        
        ctx = 'ID Consistency'
        
        # Get validationIds from JSON1
        json1_validation_ids = {
            v['validation']: v['validationId'] 
            for v in self.outputs['json1']['data']['getValidations']['validations']
            if v['statementType'] == 'KRI'
        }
        
        # Check JSON2 uses same validationIds
        for kri in self.outputs['json2']['data']['kriDetails']:
            kri_name = kri['kriName']
            for fd in kri['fundDetails']:
                expected_id = json1_validation_ids.get(kri_name)
                self.assert_equal(fd['validationId'], expected_id, 
                                 f'JSON2 {kri_name} validationId matches JSON1', ctx)
        
        # Check JSON3 kriFilter uses same validationIds
        for kf in self.outputs['json3']['data']['kriFilter']:
            kri_name = kf['kriName']
            expected_id = json1_validation_ids.get(kri_name)
            self.assert_equal(kf['validationId'], expected_id, 
                             f'JSON3 kriFilter {kri_name} validationId matches JSON1', ctx)
        
        # Check JSON5 uses same validationIds
        for kd in self.outputs['json5']['kriDetails']:
            kri_name = kd['kriName']
            expected_id = json1_validation_ids.get(kri_name)
            self.assert_equal(kd['validationId'], expected_id, 
                             f'JSON5 {kri_name} validationId matches JSON1', ctx)
        
        print()

    def test_cross_reference_integrity(self):
        """Test cross-reference integrity between Excel tabs."""
        print("=" * 80)
        print("TEST 12: CROSS-REFERENCE INTEGRITY")
        print("=" * 80)
        
        ctx = 'Cross-Ref'
        
        # All fund codes in validations should exist in funds
        valid_fund_codes = ['CAN1', 'CAN2', 'CAN3']
        
        for v in self.outputs['json1']['data']['getValidations']['validations']:
            self.assert_in(v['fund'], valid_fund_codes, f"fund {v['fund']} in valid funds", ctx)
            self.assert_in(v['fundCode'], valid_fund_codes, f"fundCode {v['fundCode']} in valid funds", ctx)
        
        # Verify group mapping is correct for each fund
        group_mapping = {'CAN1': 'A', 'CAN2': 'B', 'CAN3': 'C'}
        for v in self.outputs['json1']['data']['getValidations']['validations']:
            expected_group = group_mapping[v['fund']]
            self.assert_equal(v['group'], expected_group, 
                             f"group for {v['fund']} is {expected_group}", ctx)
        
        # Verify book mapping
        book_mapping = {
            'CAN1': 'Income Strategy Fund',
            'CAN2': 'Credit Income Fund', 
            'CAN3': 'International Bond Trust'
        }
        for v in self.outputs['json1']['data']['getValidations']['validations']:
            expected_book = book_mapping[v['fund']]
            self.assert_equal(v['book'], expected_book, 
                             f"book for {v['fund']} is {expected_book}", ctx)
        
        print()

    def run_all_tests(self):
        """Run all QA tests."""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE QA VALIDATION - EXCEL TO JSON FRAMEWORK")
        print("=" * 80 + "\n")
        
        try:
            self.setup()
            self.test_utility_functions()
            self.test_json1_structure()
            self.test_json1_validation1_trimmed()
            self.test_json1_validation2_kri()
            self.test_json1_validation3_kri()
            self.test_json1_validation4_kri()
            self.test_json2_structure_and_content()
            self.test_json3_structure_and_content()
            self.test_json4_structure_and_content()
            self.test_json5_structure_and_content()
            self.test_id_consistency_across_jsons()
            self.test_cross_reference_integrity()
        except Exception as e:
            print(f"\n!!! TEST EXECUTION ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Summary
        print("\n" + "=" * 80)
        print("QA VALIDATION SUMMARY")
        print("=" * 80)
        
        total = self.passed + self.failed
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        
        if self.failed == 0:
            print("\n✅ ALL TESTS PASSED!")
            return True
        else:
            print(f"\n❌ {self.failed} TEST(S) FAILED")
            print("\nFailed tests:")
            for error in self.errors:
                print(f"  • {error}")
            return False


if __name__ == "__main__":
    validator = QAValidator()
    success = validator.run_all_tests()
    sys.exit(0 if success else 1)
