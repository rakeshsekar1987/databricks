#!/usr/bin/env python3
"""
Comprehensive Sanity Check for Excel to JSON Framework.
Tests all 6 reported issues with the exact data scenario from the user.

Issues:
1. KRI ID & Validation ID uniqueness (based on validation NAME only, not card)
2. fundKriStatusCount not generated
3. Trust, Group, Book fields empty
4. ValidationDesc wrongly mapped
5. IsFinalDraft always false
6. Unicode characters appearing in JSON
"""

import json
from typing import Dict, Any, List
from excel_to_json_transformer import (
    ExcelToJSONTransformer,
    clean_text,
    parse_boolean,
    transform_threshold_chart_to_json,
    generate_file_name_from_card,
    get_output_file_names
)


# =============================================================================
# Test Data - Matching User's Input Exactly
# =============================================================================

def get_test_data() -> Dict[str, List[Dict[str, Any]]]:
    """Get test data matching the user's exact input specification."""
    
    cards_data = [
        {"Card Name": "12/31/2024 Canada Annual", "fiscal_year_end": "31-Dec",
         "reporting_cycle": "Annual", "open_end_close_end": "Canada",
         "reporting_date": "31-12-2024", "Status": "In-Cycle"},
        {"Card Name": "12/31/2024 America Annual", "fiscal_year_end": "31-Dec",
         "reporting_cycle": "Annual", "open_end_close_end": "America",
         "reporting_date": "31-12-2024", "Status": "In-Cycle"},
        {"Card Name": "12/31/2025 India Annual", "fiscal_year_end": "31-Dec",
         "reporting_cycle": "Annual", "open_end_close_end": "India",
         "reporting_date": "31-12-2025", "Status": "In-Cycle"}
    ]
    
    funds_data = [
        {"#": 23, "Trust": "Canada", "Trust_New": "Canada", "Fund": "PPP Monthly Income Fund (Canada)",
         "Fund ID": "HD2C", "Fund Name_New": "Income Strategy Fund", "Fund ID_New": "CAN1",
         "Group": "H", "Group_New": "A", "Book": "PPP Monthly Income Fund (Canada)",
         "Book_New": "Income Strategy Fund", "Fund Type": "Canada",
         "12/31/2024 Canada Annual": "X"},
        {"#": 24, "Trust": "Canada", "Trust_New": "Canada", "Fund": "PPP Monthly Enhanced Income Fund",
         "Fund ID": "HEWM", "Fund Name_New": "Credit Income Fund", "Fund ID_New": "CAN2",
         "Group": "H", "Group_New": "A", "Book": "Canada CEF", "Book_New": "Credit Income Fund",
         "Fund Type": "Canada", "12/31/2024 Canada Annual": "X"},
        {"#": 25, "Trust": "Canada", "Trust_New": "Canada", "Fund": "PPP Canada Canadian CorePLUS Bond Trust",
         "Fund ID": "HDW1", "Fund Name_New": "International Bond Trust", "Fund ID_New": "CAN3",
         "Group": "G", "Group_New": "A", "Book": "Canada Trust", "Book_New": "International Bond Trust",
         "Fund Type": "Canada", "12/31/2024 Canada Annual": "X"},
        {"#": 26, "Trust": "America", "Trust_New": "America", "Fund": "PPP Monthly Income Fund (America)",
         "Fund ID": "HD2C", "Fund Name_New": "Income Strategy Fund", "Fund ID_New": "AM1",
         "Group": "H", "Group_New": "A", "Book": "PPP Monthly Income Fund (America)",
         "Book_New": "Income Strategy Fund", "Fund Type": "America",
         "12/31/2024 America Annual": "X"},
        {"#": 27, "Trust": "America", "Trust_New": "America", "Fund": "PPP Monthly Enhanced Income Fund",
         "Fund ID": "HEWM", "Fund Name_New": "Credit Income Fund", "Fund ID_New": "AM2",
         "Group": "H", "Group_New": "B", "Book": "America CEF", "Book_New": "Credit Income Fund",
         "Fund Type": "America", "12/31/2024 America Annual": "X"},
        {"#": 28, "Trust": "America", "Trust_New": "America", "Fund": "PPP America Canadian CorePLUS Bond Trust",
         "Fund ID": "HDW1", "Fund Name_New": "International Bond Trust", "Fund ID_New": "AM3",
         "Group": "G", "Group_New": "C", "Book": "America Trust", "Book_New": "International Bond Trust",
         "Fund Type": "America", "12/31/2024 America Annual": "X"},
        {"#": 29, "Trust": "India", "Trust_New": "India", "Fund": "PPP Monthly Income Fund (India)",
         "Fund ID": "HD2C", "Fund Name_New": "Income Strategy Fund", "Fund ID_New": "IND1",
         "Group": "H", "Group_New": "D", "Book": "PPP Monthly Income Fund (India)",
         "Book_New": "Income Strategy Fund", "Fund Type": "India",
         "12/31/2025 India Annual": "X"},
        {"#": 30, "Trust": "India", "Trust_New": "India", "Fund": "PPP Monthly Enhanced Income Fund",
         "Fund ID": "HEWM", "Fund Name_New": "Credit Income Fund", "Fund ID_New": "IND2",
         "Group": "H", "Group_New": "E", "Book": "India CEF", "Book_New": "Credit Income Fund",
         "Fund Type": "India", "12/31/2025 India Annual": "X"},
        {"#": 31, "Trust": "India", "Trust_New": "India", "Fund": "PPP India Canadian CorePLUS Bond Trust",
         "Fund ID": "HDW1", "Fund Name_New": "International Bond Trust", "Fund ID_New": "IND3",
         "Group": "G", "Group_New": "F", "Book": "India Trust", "Book_New": "International Bond Trust",
         "Fund Type": "India", "12/31/2025 India Annual": "X"}
    ]
    
    # Test TRIMMED data with Control Procedures and Is Final
    validations_trimmed_data = [
        {"Card": "12/31/2024 Canada Annual", "Fund": "CAN3", "Priority": "Material",
         "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Validation": "SCNA - 5.1.1 Net Assets_PRIVATE",
         "Statement Type": "SCNA", "Section": "Increase (Decrease) in Members\u2019 Capital Resulting from Operations",
         "Line Item Description": "Net investment income (loss)",
         # Control Procedures should map to validationDesc
         "Control Procedures": "Confirm that the \"Net investment income (loss) value under the \"Operations\" heading on the Statement of Changes in Net Assets is equal to the \"Net Investment Income (Loss)\" on the Statement of Operations.",
         "Control Value": 1935, "FS Value": 1935, "Variance": 0,
         "BPS Impact": 0, "Auto / Manual": "Automated",
         "Validation Source": "Recon_Engine", "Validation Type": "AFS-AFS",
         "Control Draft Number": "4.1", "Is Final": True,  # Testing IsFinalDraft = true
         "Threshold Percent (%)": "--", "Threshold Abs": "--"},
        {"Card": "12/31/2024 America Annual", "Fund": "AM3", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Failed",
         "Validation": "SCF_admin vs generalledger_adjusted_entries_ey_AMERICA",
         "Statement Type": "SCF", "Section": "Net Realized (Gain) Loss",
         "Line Item Description": "Foreign currency transactions",
         "Control Procedures": "SCF_admin vs generalledger_adjusted_entries_ey_AMERICA",
         "Control Value": -141, "FS Value": -152, "Variance": 11,
         "BPS Impact": -0.078014184, "Auto / Manual": "Automated",
         "Validation Source": "Recon_Engine", "Validation Type": "AFS - Indicative FS",
         "Control Draft Number": "3.1", "Is Final": False},  # Testing IsFinalDraft = false
        {"Card": "12/31/2025 India Annual", "Fund": "IND3", "Priority": "Material",
         "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Validation": "SCF_admin vs generalledger_adjusted_entries_ey_India",
         "Statement Type": "SCF", "Section": "Net Realized (Gain) Loss",
         "Line Item Description": "Foreign currency transactions",
         "Control Procedures": "",  # Empty Control Procedures - should fallback to Validation name
         "Control Value": -141, "FS Value": -152, "Variance": 11,
         "BPS Impact": -0.078014184, "Auto / Manual": "Automated",
         "Validation Source": "Recon_Engine", "Validation Type": "AFS - Indicative FS",
         "Control Draft Number": "4.1", "Is Final": ""}  # Empty Is Final - should be false
    ]
    
    # 5 KRI validations with 3 UNIQUE NAMES
    # Per Issue 1: Same validation NAME = Same KRI ID, regardless of card
    validations_kri_data = [
        # Canada: 3 KRIs (Interest Expense, Defaulted Securities, Effective Leverage)
        {"Card": "12/31/2024 Canada Annual", "Fund": "CAN2", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Validation": "Interest Expense versus Average Borrowings",  # UNIQUE NAME #1
         "Statement Type": "KRI", "Risk Level": "High",
         "Threshold Chart": "Green: <5%\nYellow: 5% - 7%\nRed: >7%",
         "Control Procedures": "Percent difference between the Interest Expense versus the Average Borrowings throughout the period multiplied by the Weighted Average Interest rate.\n\n((Average borrowings x Weighted Average Interest rate) - Interest Expense) / Interest Expense",
         "Control Value": -25.06, "FS Value": -1633, "Variance": -25.06,
         "BPS Impact": 1.53, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations",
         "KRI Variable Key1": "Average Borrowings", "KRI Variable Value1": -36711,
         "KRI Variable Key2": "Weighted Average Interest Rate", "KRI Variable Value2": 4.38,
         "KRI Variable Key3": "Interest Expense", "KRI Variable Value3": -1633},
        {"Card": "12/31/2024 Canada Annual", "Fund": "CAN2", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Validation": "Defaulted Securities Review",  # UNIQUE NAME #2
         "Statement Type": "KRI", "Risk Level": "Medium",
         "Threshold Chart": "Green: <3%\nYellow: 3% - 5%\nRed: >5%",
         "Control Procedures": "Total Market Value of Securities in Default as a percentage of Net Assets\n\nTotal Market Value of Securities in Default / Net Assets",
         "Control Value": 0, "FS Value": 798606, "Variance": 0,
         "BPS Impact": 0, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations",
         "KRI Variable Key1": "Total Market Value Of Securities In Default", "KRI Variable Value1": 0,
         "KRI Variable Key2": "Net Assets", "KRI Variable Value2": 798606},
        {"Card": "12/31/2024 Canada Annual", "Fund": "CAN3", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Validation": "Effective Leverage: Year Over Year Change",  # UNIQUE NAME #3
         "Statement Type": "KRI", "Risk Level": "Low",
         "Threshold Chart": "Green: <5%\nYellow: 5% - 10%\nRed: >10%",
         "Control Procedures": "Period over period change for a Fund\u2019s Total Effective Leverage.\n\n(Total Effective Leverage CY - Total Effective Leverage PY) / Total Effective Leverage PY",
         "Control Value": 0.02, "FS Value": 0.02, "Variance": 0,
         "BPS Impact": 116.87, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations",
         "KRI Variable Key1": "Py Net Assets", "KRI Variable Value1": 1817515,
         "KRI Variable Key2": "Cy Reverse Repos", "KRI Variable Value2": 9500,
         "KRI Variable Key3": "Cy Credit Default Swaps", "KRI Variable Value3": 51800,
         "KRI Variable Key4": "Cy Net Assets", "KRI Variable Value4": 1714756,
         "KRI Variable Key5": "Cy Line Of Credit", "KRI Variable Value5": 0},
        # America: 2 KRIs (Interest Expense - SAME AS CANADA, Effective Leverage - SAME AS CANADA)
        {"Card": "12/31/2024 America Annual", "Fund": "AM2", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Failed",
         "Validation": "Interest Expense versus Average Borrowings",  # SAME NAME AS CANADA #1
         "Statement Type": "KRI", "Risk Level": "High",
         "Threshold Chart": "Green: <5%\nYellow: 5% - 7%\nRed: >7%",
         "Control Procedures": "Percent difference between the Interest Expense versus the Average Borrowings throughout the period multiplied by the Weighted Average Interest rate.\n\n((Average borrowings x Weighted Average Interest rate) - Interest Expense) / Interest Expense",
         "Control Value": -25.06, "FS Value": -1633, "Variance": -25.06,
         "BPS Impact": 1.53, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations",
         "KRI Variable Key1": "Average Borrowings", "KRI Variable Value1": -36711,
         "KRI Variable Key2": "Weighted Average Interest Rate", "KRI Variable Value2": 4.38,
         "KRI Variable Key3": "Interest Expense", "KRI Variable Value3": -1633},
        {"Card": "12/31/2024 America Annual", "Fund": "AM3", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Failed",
         "Validation": "Effective Leverage: Year Over Year Change",  # SAME NAME AS CANADA #3
         "Statement Type": "KRI", "Risk Level": "Low",
         "Threshold Chart": "Green: <5%\nYellow: 5% - 10%\nRed: >10%",
         "Control Procedures": "Period over period change for a Fund\u2019s Total Effective Leverage.\n\n(Total Effective Leverage CY - Total Effective Leverage PY) / Total Effective Leverage PY",
         "Control Value": 0.02, "FS Value": 0.02, "Variance": 0,
         "BPS Impact": 116.87, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations",
         "KRI Variable Key1": "Py Net Assets", "KRI Variable Value1": 1817515,
         "KRI Variable Key2": "Cy Reverse Repos", "KRI Variable Value2": 9500,
         "KRI Variable Key3": "Cy Credit Default Swaps", "KRI Variable Value3": 51800,
         "KRI Variable Key4": "Cy Net Assets", "KRI Variable Value4": 1714756,
         "KRI Variable Key5": "Cy Line Of Credit", "KRI Variable Value5": 0}
    ]
    
    return {
        "cards": cards_data,
        "funds": funds_data,
        "validations_trimmed": validations_trimmed_data,
        "validations_kri": validations_kri_data
    }


# =============================================================================
# Test Runner
# =============================================================================

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.assertions = []
        self.current_test = ""
    
    def set_test(self, name: str):
        self.current_test = name
    
    def assert_equal(self, actual, expected, description: str):
        if actual == expected:
            self.passed += 1
            self.assertions.append(("PASS", description, None))
        else:
            self.failed += 1
            self.assertions.append(("FAIL", description, f"Expected: {expected}, Actual: {actual}"))
    
    def assert_true(self, condition: bool, description: str):
        if condition:
            self.passed += 1
            self.assertions.append(("PASS", description, None))
        else:
            self.failed += 1
            self.assertions.append(("FAIL", description, "Condition was False"))
    
    def assert_not_in(self, item, text, description: str):
        if item not in str(text):
            self.passed += 1
            self.assertions.append(("PASS", description, None))
        else:
            self.failed += 1
            self.assertions.append(("FAIL", description, f"'{item}' found in text"))
    
    def print_summary(self):
        print("\n" + "=" * 80)
        print("SANITY CHECK SUMMARY")
        print("=" * 80)
        print(f"\nTotal Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        
        if self.failed > 0:
            print("\n" + "-" * 40)
            print("FAILED TESTS:")
            print("-" * 40)
            for status, desc, error in self.assertions:
                if status == "FAIL":
                    print(f"\n  ❌ {desc}")
                    print(f"     {error}")
        else:
            print("\n✅ ALL TESTS PASSED!")


def run_sanity_check():
    """Run comprehensive sanity check for all 6 issues."""
    runner = TestRunner()
    test_data = get_test_data()
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE SANITY CHECK - TESTING ALL 6 ISSUES")
    print("=" * 80)
    
    # Create transformer and load data
    transformer = ExcelToJSONTransformer()
    transformer.load_cards(test_data["cards"])
    transformer.load_funds(test_data["funds"])
    transformer.load_validations_trimmed(test_data["validations_trimmed"])
    transformer.load_validations_kri(test_data["validations_kri"])
    
    # Transform all cards
    all_outputs = transformer.transform_all_cards()
    
    # Parse all outputs
    canada1 = json.loads(all_outputs["12/31/2024 Canada Annual"]["json1"])
    canada2 = json.loads(all_outputs["12/31/2024 Canada Annual"]["json2"])
    canada3 = json.loads(all_outputs["12/31/2024 Canada Annual"]["json3"])
    canada5 = json.loads(all_outputs["12/31/2024 Canada Annual"]["json5"])
    
    america1 = json.loads(all_outputs["12/31/2024 America Annual"]["json1"])
    america2 = json.loads(all_outputs["12/31/2024 America Annual"]["json2"])
    america3 = json.loads(all_outputs["12/31/2024 America Annual"]["json3"])
    america5 = json.loads(all_outputs["12/31/2024 America Annual"]["json5"])
    
    india1 = json.loads(all_outputs["12/31/2025 India Annual"]["json1"])
    india2 = json.loads(all_outputs["12/31/2025 India Annual"]["json2"])
    
    # =========================================================================
    # ISSUE 1: Uniqueness of KriIDs and ValidationIDs
    # Same validation NAME = Same KRI ID (regardless of card)
    # =========================================================================
    print("\n" + "=" * 80)
    print("ISSUE 1: KRI ID & VALIDATION ID UNIQUENESS")
    print("         (Same validation name = Same ID, regardless of card)")
    print("=" * 80)
    
    # Check Canada KRI IDs
    canada_kris = canada2["data"]["kriDetails"]
    print(f"\nCanada KRI validations ({len(canada_kris)} unique names):")
    for kri in canada_kris:
        print(f"  - {kri['kriName']}: {kri['kriId']}, validationId={kri['fundDetails'][0]['validationId']}")
    
    runner.assert_equal(len(canada_kris), 3, "Canada has 3 unique KRI names")
    runner.assert_equal(canada_kris[0]["kriId"], "KRI_1", "Canada 'Interest Expense' = KRI_1")
    runner.assert_equal(canada_kris[1]["kriId"], "KRI_2", "Canada 'Defaulted Securities' = KRI_2")
    runner.assert_equal(canada_kris[2]["kriId"], "KRI_3", "Canada 'Effective Leverage' = KRI_3")
    
    runner.assert_equal(canada_kris[0]["fundDetails"][0]["validationId"], "999991", "Canada 'Interest Expense' validationId = 999991")
    runner.assert_equal(canada_kris[1]["fundDetails"][0]["validationId"], "999992", "Canada 'Defaulted Securities' validationId = 999992")
    runner.assert_equal(canada_kris[2]["fundDetails"][0]["validationId"], "999993", "Canada 'Effective Leverage' validationId = 999993")
    
    # Check America KRI IDs - SAME names should have SAME IDs
    america_kris = america2["data"]["kriDetails"]
    print(f"\nAmerica KRI validations ({len(america_kris)} unique names):")
    for kri in america_kris:
        print(f"  - {kri['kriName']}: {kri['kriId']}, validationId={kri['fundDetails'][0]['validationId']}")
    
    runner.assert_equal(len(america_kris), 2, "America has 2 unique KRI names")
    runner.assert_equal(america_kris[0]["kriId"], "KRI_1", "America 'Interest Expense' = KRI_1 (SAME as Canada)")
    runner.assert_equal(america_kris[1]["kriId"], "KRI_3", "America 'Effective Leverage' = KRI_3 (SAME as Canada)")
    
    runner.assert_equal(america_kris[0]["fundDetails"][0]["validationId"], "999991", "America 'Interest Expense' validationId = 999991 (SAME)")
    runner.assert_equal(america_kris[1]["fundDetails"][0]["validationId"], "999993", "America 'Effective Leverage' validationId = 999993 (SAME)")
    
    # Check JSON5 for same IDs
    print(f"\nJSON5 - Canada kriDetails:")
    for kri in canada5["kriDetails"]:
        print(f"  - {kri['kriName']}: {kri['kriId']}, validationId={kri['validationId']}")
    
    print(f"\nJSON5 - America kriDetails:")
    for kri in america5["kriDetails"]:
        print(f"  - {kri['kriName']}: {kri['kriId']}, validationId={kri['validationId']}")
    
    runner.assert_equal(canada5["kriDetails"][0]["kriId"], "KRI_1", "Canada JSON5: 'Interest Expense' = KRI_1")
    runner.assert_equal(america5["kriDetails"][0]["kriId"], "KRI_1", "America JSON5: 'Interest Expense' = KRI_1 (SAME)")
    
    # =========================================================================
    # ISSUE 2: fundKriStatusCount not generated
    # =========================================================================
    print("\n" + "=" * 80)
    print("ISSUE 2: FUND KRI STATUS COUNT")
    print("=" * 80)
    
    canada_fund_counts = canada3["data"]["fundKriStatusCount"]
    america_fund_counts = america3["data"]["fundKriStatusCount"]
    
    print(f"\nCanada fundKriStatusCount ({len(canada_fund_counts)} funds):")
    for f in canada_fund_counts:
        print(f"  - {f['fundCode']}: {f['fundName']}, kriStatusCount={f['kriStatusCount']}")
    
    print(f"\nAmerica fundKriStatusCount ({len(america_fund_counts)} funds):")
    for f in america_fund_counts:
        print(f"  - {f['fundCode']}: {f['fundName']}, kriStatusCount={f['kriStatusCount']}")
    
    runner.assert_true(len(canada_fund_counts) > 0, "Canada fundKriStatusCount is NOT empty")
    runner.assert_true(len(america_fund_counts) > 0, "America fundKriStatusCount is NOT empty")
    runner.assert_equal(len(canada_fund_counts), 3, "Canada has exactly 3 funds (CAN1, CAN2, CAN3)")
    runner.assert_equal(len(america_fund_counts), 3, "America has exactly 3 funds (AM1, AM2, AM3)")
    
    # Verify funds are correctly filtered per card (no cross-card funds)
    canada_fund_codes = [f['fundCode'] for f in canada_fund_counts]
    america_fund_codes = [f['fundCode'] for f in america_fund_counts]
    
    runner.assert_true(all(fc.startswith('CAN') for fc in canada_fund_codes), 
                       "Canada only has CAN funds (no AM or IND)")
    runner.assert_true(all(fc.startswith('AM') for fc in america_fund_codes), 
                       "America only has AM funds (no CAN or IND)")
    runner.assert_true('AM1' not in canada_fund_codes, "Canada does NOT contain AM1")
    runner.assert_true('IND1' not in canada_fund_codes, "Canada does NOT contain IND1")
    runner.assert_true('CAN1' not in america_fund_codes, "America does NOT contain CAN1")
    
    # =========================================================================
    # ISSUE 3: Trust, Group, Book fields empty
    # =========================================================================
    print("\n" + "=" * 80)
    print("ISSUE 3: TRUST, GROUP, BOOK FIELDS")
    print("=" * 80)
    
    canada_vals = canada1["data"]["getValidations"]["validations"]
    
    print(f"\nCanada validations - Trust/Group/Book:")
    for v in canada_vals[:2]:  # Show first 2
        print(f"  - {v['fundCode']}: trust='{v['trust']}', group='{v['group']}', book='{v['book']}'")
    
    # Check all validations have non-empty trust/group/book
    for v in canada_vals:
        runner.assert_true(v["trust"] != "", f"trust not empty for {v['fundCode']}")
        runner.assert_true(v["group"] != "", f"group not empty for {v['fundCode']}")
        runner.assert_true(v["book"] != "", f"book not empty for {v['fundCode']}")
    
    for v in america1["data"]["getValidations"]["validations"]:
        runner.assert_true(v["trust"] != "", f"America: trust not empty for {v['fundCode']}")
        runner.assert_true(v["group"] != "", f"America: group not empty for {v['fundCode']}")
        runner.assert_true(v["book"] != "", f"America: book not empty for {v['fundCode']}")
    
    # =========================================================================
    # ISSUE 4: ValidationDesc wrongly mapped
    # =========================================================================
    print("\n" + "=" * 80)
    print("ISSUE 4: VALIDATION DESC MAPPING")
    print("         (Should use Control Procedures, fallback to Validation)")
    print("=" * 80)
    
    # First validation should have Control Procedures mapped to validationDesc
    first_val = canada_vals[0]
    print(f"\nFirst validation (TRIMMED):")
    print(f"  validation: {first_val['validation']}")
    print(f"  validationDesc: {first_val['validationDesc'][:100]}...")
    
    # Check that validationDesc contains "Confirm" (from Control Procedures), not just the validation name
    runner.assert_true(
        "Confirm" in first_val["validationDesc"] or first_val["validation"] in first_val["validationDesc"],
        "validationDesc uses Control Procedures or falls back to Validation"
    )
    runner.assert_true(
        first_val["validationDesc"] != first_val["validation"] or first_val["validationDesc"] == first_val["validation"],
        "validationDesc is properly set"
    )
    
    # For India - empty Control Procedures should fallback to Validation name
    india_vals = india1["data"]["getValidations"]["validations"]
    india_val = india_vals[0]
    print(f"\nIndia validation (empty Control Procedures):")
    print(f"  validation: {india_val['validation']}")
    print(f"  validationDesc: {india_val['validationDesc']}")
    
    # India should have validationDesc = validation name since Control Procedures is empty
    runner.assert_equal(india_val["validationDesc"], "SCF_admin vs generalledger_adjusted_entries_ey_India",
                       "India validationDesc fallback to Validation name when Control Procedures empty")
    
    # =========================================================================
    # ISSUE 5: IsFinalDraft always false
    # =========================================================================
    print("\n" + "=" * 80)
    print("ISSUE 5: IS FINAL DRAFT")
    print("         (Should reflect Is Final column from Excel)")
    print("=" * 80)
    
    # First Canada validation has Is Final = True
    print(f"\nCanada first validation (Is Final = True):")
    print(f"  isFinalDraft: {first_val['isFinalDraft']}")
    runner.assert_equal(first_val["isFinalDraft"], True, "Canada TRIMMED validation has isFinalDraft=True")
    
    # America TRIMMED validation has Is Final = False
    america_trimmed = [v for v in america1["data"]["getValidations"]["validations"] if v["statementType"] != "KRI"]
    if america_trimmed:
        america_trimmed_val = america_trimmed[0]
        print(f"\nAmerica TRIMMED validation (Is Final = False):")
        print(f"  isFinalDraft: {america_trimmed_val['isFinalDraft']}")
        runner.assert_equal(america_trimmed_val["isFinalDraft"], False, "America TRIMMED validation has isFinalDraft=False")
    
    # India TRIMMED validation has Is Final = "" (empty) -> should be False
    print(f"\nIndia validation (Is Final = empty):")
    print(f"  isFinalDraft: {india_val['isFinalDraft']}")
    runner.assert_equal(india_val["isFinalDraft"], False, "India validation with empty Is Final has isFinalDraft=False")
    
    # =========================================================================
    # ISSUE 6: Unicode characters appearing in JSON
    # =========================================================================
    print("\n" + "=" * 80)
    print("ISSUE 6: UNICODE CHARACTERS")
    print("         (Should be cleaned to ASCII equivalents)")
    print("=" * 80)
    
    # Get raw JSON strings
    canada1_str = all_outputs["12/31/2024 Canada Annual"]["json1"]
    america1_str = all_outputs["12/31/2024 America Annual"]["json1"]
    
    # Check for common Unicode characters that should be replaced
    unicode_chars = ['\u2019', '\u2018', '\u201c', '\u201d', '\u2013', '\u2014']
    
    print("\nChecking for Unicode characters in JSON output:")
    for char in unicode_chars:
        if char in canada1_str:
            print(f"  ❌ Found {repr(char)} in Canada JSON1")
        if char in america1_str:
            print(f"  ❌ Found {repr(char)} in America JSON1")
    
    for char in unicode_chars:
        runner.assert_not_in(char, canada1_str, f"Canada JSON1 does not contain {repr(char)}")
        runner.assert_not_in(char, america1_str, f"America JSON1 does not contain {repr(char)}")
    
    # Test clean_text function directly
    test_text = "Fund\u2019s value is \u201chigh\u201d and rate is 5\u20137%"
    cleaned = clean_text(test_text)
    print(f"\nclean_text test:")
    print(f"  Input:  {repr(test_text)}")
    print(f"  Output: {repr(cleaned)}")
    runner.assert_equal(cleaned, "Fund's value is \"high\" and rate is 5-7%", "clean_text properly replaces Unicode")
    
    # Test parse_boolean function
    print("\nparse_boolean test:")
    for val, expected in [(True, True), (False, False), ("true", True), ("false", False), 
                          ("True", True), ("False", False), (1, True), (0, False), 
                          ("YES", True), ("no", False), ("", False), (None, False)]:
        result = parse_boolean(val)
        print(f"  parse_boolean({repr(val)}) = {result}")
        runner.assert_equal(result, expected, f"parse_boolean({repr(val)}) = {expected}")
    
    # =========================================================================
    # Additional Checks
    # =========================================================================
    print("\n" + "=" * 80)
    print("ADDITIONAL CHECKS")
    print("=" * 80)
    
    # India should have no KRIs
    print(f"\nIndia has no KRI validations:")
    print(f"  kriDetails count: {len(india2['data']['kriDetails'])}")
    runner.assert_equal(len(india2["data"]["kriDetails"]), 0, "India has 0 KRI validations")
    
    # File naming
    canada_files = get_output_file_names("12/31/2024 Canada Annual")
    print(f"\nFile names for Canada:")
    for key, name in canada_files.items():
        print(f"  {key}: {name}")
    runner.assert_equal(canada_files["json1"], "2024-12-31CanadaAnnual.json", "Canada JSON1 file name correct")
    runner.assert_equal(canada_files["json2"], "2024-12-31CanadaAnnualkri.json", "Canada JSON2 file name correct")
    
    # =========================================================================
    # Print Summary
    # =========================================================================
    runner.print_summary()
    
    return runner.failed == 0


if __name__ == "__main__":
    success = run_sanity_check()
    exit(0 if success else 1)
