#!/usr/bin/env python3
"""
Comprehensive QA Validation for Excel to JSON Framework.
Tests multi-card processing, card-based filtering, and data integrity.
"""

import json
from typing import Dict, Any, List
from excel_to_json_transformer import (
    ExcelToJSONTransformer,
    clean_text,
    parse_number,
    transform_threshold_chart_to_json,
    generate_file_name_from_card,
    get_output_file_names,
    GlobalKRIMappingService
)


# =============================================================================
# Test Data - Multi-Card Scenario
# =============================================================================

def get_test_data() -> Dict[str, List[Dict[str, Any]]]:
    """Get test data matching the user's input specification."""
    
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
        },
        {
            "Card Name": "12/31/2025 India Annual",
            "fiscal_year_end": "31-Dec",
            "reporting_cycle": "Annual",
            "open_end_close_end": "India",
            "reporting_date": "31-12-2025",
            "Status": "In-Cycle"
        }
    ]
    
    funds_data = [
        # Canada funds
        {"#": 23, "Trust": "Canada", "Trust_New": "Canada", "Fund": "PPP Monthly Income Fund (Canada)",
         "Fund ID": "HD2C", "Fund Name_New": "Income Strategy Fund", "Fund ID_New": "CAN1",
         "Group": "H", "Group_New": "A", "Book": "PPP Monthly Income Fund (Canada)",
         "Book_New": "Income Strategy Fund", "Fund Type": "Canada"},
        {"#": 24, "Trust": "Canada", "Trust_New": "Canada", "Fund": "PPP Monthly Enhanced Income Fund",
         "Fund ID": "HEWM", "Fund Name_New": "Credit Income Fund", "Fund ID_New": "CAN2",
         "Group": "H", "Group_New": "A", "Book": "Canada CEF",
         "Book_New": "Credit Income Fund", "Fund Type": "Canada"},
        {"#": 25, "Trust": "Canada", "Trust_New": "Canada", "Fund": "PPP Canada Canadian CorePLUS Bond Trust",
         "Fund ID": "HDW1", "Fund Name_New": "International Bond Trust", "Fund ID_New": "CAN3",
         "Group": "G", "Group_New": "A", "Book": "Canada Trust",
         "Book_New": "International Bond Trust", "Fund Type": "Canada"},
        # America funds
        {"#": 26, "Trust": "America", "Trust_New": "America", "Fund": "PPP Monthly Income Fund (America)",
         "Fund ID": "HD2C", "Fund Name_New": "Income Strategy Fund", "Fund ID_New": "AM1",
         "Group": "H", "Group_New": "A", "Book": "PPP Monthly Income Fund (America)",
         "Book_New": "Income Strategy Fund", "Fund Type": "America"},
        {"#": 27, "Trust": "America", "Trust_New": "America", "Fund": "PPP Monthly Enhanced Income Fund",
         "Fund ID": "HEWM", "Fund Name_New": "Credit Income Fund", "Fund ID_New": "AM2",
         "Group": "H", "Group_New": "B", "Book": "America CEF",
         "Book_New": "Credit Income Fund", "Fund Type": "America"},
        {"#": 28, "Trust": "America", "Trust_New": "America", "Fund": "PPP America Canadian CorePLUS Bond Trust",
         "Fund ID": "HDW1", "Fund Name_New": "International Bond Trust", "Fund ID_New": "AM3",
         "Group": "G", "Group_New": "C", "Book": "America Trust",
         "Book_New": "International Bond Trust", "Fund Type": "America"},
        # India funds
        {"#": 29, "Trust": "India", "Trust_New": "India", "Fund": "PPP Monthly Income Fund (India)",
         "Fund ID": "HD2C", "Fund Name_New": "Income Strategy Fund", "Fund ID_New": "IND1",
         "Group": "H", "Group_New": "D", "Book": "PPP Monthly Income Fund (India)",
         "Book_New": "Income Strategy Fund", "Fund Type": "India"},
        {"#": 30, "Trust": "India", "Trust_New": "India", "Fund": "PPP Monthly Enhanced Income Fund",
         "Fund ID": "HEWM", "Fund Name_New": "Credit Income Fund", "Fund ID_New": "IND2",
         "Group": "H", "Group_New": "E", "Book": "India CEF",
         "Book_New": "Credit Income Fund", "Fund Type": "India"},
        {"#": 31, "Trust": "India", "Trust_New": "India", "Fund": "PPP India Canadian CorePLUS Bond Trust",
         "Fund ID": "HDW1", "Fund Name_New": "International Bond Trust", "Fund ID_New": "IND3",
         "Group": "G", "Group_New": "F", "Book": "India Trust",
         "Book_New": "International Bond Trust", "Fund Type": "India"}
    ]
    
    validations_trimmed_data = [
        {
            "Card": "12/31/2024 Canada Annual", "Fund": "CAN3", "Priority": "Material",
            "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
            "Validation": "SCF_admin vs generalledger_adjusted_entries_ey_CANADA",
            "Statement Type": "SCF", "Section": "Net Realized (Gain) Loss",
            "Line Item Description": "Foreign currency transactions",
            "Control Procedures": "SCF_admin vs generalledger_adjusted_entries_ey_CANADA",
            "Control Value": -141, "FS Value": -152, "Variance": 11,
            "BPS Impact": -0.078014184, "Auto / Manual": "Automated",
            "Validation Source": "Recon_Engine", "Validation Type": "AFS - Indicative FS",
            "Control Draft Number": "2.1", "Threshold Percent (%)": "--", "Threshold Abs": "--"
        },
        {
            "Card": "12/31/2025 America Annual", "Fund": "AM3", "Priority": "Standard",
            "Workflow Status": "EY L1 Review", "Validation Status": "Failed",
            "Validation": "SCF_admin vs generalledger_adjusted_entries_ey_AMERICA",
            "Statement Type": "SCF", "Section": "Net Realized (Gain) Loss",
            "Line Item Description": "Foreign currency transactions",
            "Control Procedures": "SCF_admin vs generalledger_adjusted_entries_ey_AMERICA",
            "Control Value": -141, "FS Value": -152, "Variance": 11,
            "BPS Impact": -0.078014184, "Auto / Manual": "Automated",
            "Validation Source": "Recon_Engine", "Validation Type": "AFS - Indicative FS",
            "Control Draft Number": "3.1", "Threshold Percent (%)": "--", "Threshold Abs": "--"
        },
        {
            "Card": "12/31/2025 India Annual", "Fund": "IND3", "Priority": "Material",
            "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
            "Validation": "SCF_admin vs generalledger_adjusted_entries_ey_India",
            "Statement Type": "SCF", "Section": "Net Realized (Gain) Loss",
            "Line Item Description": "Foreign currency transactions",
            "Control Procedures": "SCF_admin vs generalledger_adjusted_entries_ey_India",
            "Control Value": -141, "FS Value": -152, "Variance": 11,
            "BPS Impact": -0.078014184, "Auto / Manual": "Automated",
            "Validation Source": "Recon_Engine", "Validation Type": "AFS - Indicative FS",
            "Control Draft Number": "4.1", "Threshold Percent (%)": "--", "Threshold Abs": "--"
        }
    ]
    
    validations_kri_data = [
        # Canada KRI validations
        {
            "Card": "12/31/2024 Canada Annual", "Fund": "CAN2", "Priority": "Standard",
            "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
            "Validation": "Interest Expense versus Average Borrowings",
            "Statement Type": "KRI", "Risk Level": "High",
            "Threshold Chart": "Green: <5%\nYellow: 5% - 7%\nRed: >7%",
            "Control Procedures": "Percent difference between the Interest Expense versus the Average Borrowings throughout the period multiplied by the Weighted Average Interest rate. ((Average borrowings x Weighted Average Interest rate) - Interest Expense) / Interest Expense",
            "Control Value": -25.06, "FS Value": -1633, "Variance": -25.06,
            "BPS Impact": 1.53, "Auto / Manual": "Automated",
            "Validation Source": "KRI Validations", "Validation Type": "KRI Validations",
            "Control Draft Number": "null.1",
            "KRI Variable Key1": "Average Borrowings", "KRI Variable Value1": -36711,
            "KRI Variable Key2": "Weighted Average Interest Rate", "KRI Variable Value2": 4.38,
            "KRI Variable Key3": "Interest Expense", "KRI Variable Value3": -1633
        },
        {
            "Card": "12/31/2024 Canada Annual", "Fund": "CAN2", "Priority": "Standard",
            "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
            "Validation": "Defaulted Securities Review",
            "Statement Type": "KRI", "Risk Level": "Medium",
            "Threshold Chart": "Green: <3%\nYellow: 3% - 5%\nRed: >5%",
            "Control Procedures": "Total Market Value of Securities in Default as a percentage of Net Assets. Total Market Value of Securities in Default / Net Assets",
            "Control Value": 0, "FS Value": "7,98,606.00", "Variance": 0,
            "BPS Impact": 0, "Auto / Manual": "Automated",
            "Validation Source": "KRI Validations", "Validation Type": "KRI Validations",
            "Control Draft Number": "null.1",
            "KRI Variable Key1": "Total Market Value Of Securities In Default", "KRI Variable Value1": 0,
            "KRI Variable Key2": "Net Assets", "KRI Variable Value2": "7,98,606.00"
        },
        {
            "Card": "12/31/2024 Canada Annual", "Fund": "CAN3", "Priority": "Standard",
            "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
            "Validation": "Effective Leverage: Year Over Year Change",
            "Statement Type": "KRI", "Risk Level": "Low",
            "Threshold Chart": "Green: <5%\nYellow: 5% - 10%\nRed: >10%",
            "Control Procedures": "Period over period change for a Fund's Total Effective Leverage. (Total Effective Leverage CY - Total Effective Leverage PY) / Total Effective Leverage PY",
            "Control Value": 0.02, "FS Value": 0.02, "Variance": 0,
            "BPS Impact": 116.87, "Auto / Manual": "Automated",
            "Validation Source": "KRI Validations", "Validation Type": "KRI Validations",
            "Control Draft Number": "null.1",
            "KRI Variable Key1": "Py Net Assets", "KRI Variable Value1": "18,17,515.00",
            "KRI Variable Key2": "Cy Reverse Repos", "KRI Variable Value2": "9,500.00",
            "KRI Variable Key3": "Cy Credit Default Swaps", "KRI Variable Value3": "51,800.00",
            "KRI Variable Key4": "Cy Net Assets", "KRI Variable Value4": "17,14,756.00",
            "KRI Variable Key5": "Cy Line Of Credit", "KRI Variable Value5": 0
        },
        # America KRI validations (only 2 - no Defaulted Securities)
        {
            "Card": "12/31/2025 America Annual", "Fund": "AM2", "Priority": "Standard",
            "Workflow Status": "EY L1 Review", "Validation Status": "Failed",
            "Validation": "Interest Expense versus Average Borrowings",
            "Statement Type": "KRI", "Risk Level": "High",
            "Threshold Chart": "Green: <5%\nYellow: 5% - 7%\nRed: >7%",
            "Control Procedures": "Percent difference between the Interest Expense versus the Average Borrowings throughout the period multiplied by the Weighted Average Interest rate. ((Average borrowings x Weighted Average Interest rate) - Interest Expense) / Interest Expense",
            "Control Value": -25.06, "FS Value": -1633, "Variance": -25.06,
            "BPS Impact": 1.53, "Auto / Manual": "Automated",
            "Validation Source": "KRI Validations", "Validation Type": "KRI Validations",
            "Control Draft Number": "null.1",
            "KRI Variable Key1": "Average Borrowings", "KRI Variable Value1": -36711,
            "KRI Variable Key2": "Weighted Average Interest Rate", "KRI Variable Value2": 4.38,
            "KRI Variable Key3": "Interest Expense", "KRI Variable Value3": -1633
        },
        {
            "Card": "12/31/2025 America Annual", "Fund": "AM3", "Priority": "Standard",
            "Workflow Status": "EY L1 Review", "Validation Status": "Failed",
            "Validation": "Effective Leverage: Year Over Year Change",
            "Statement Type": "KRI", "Risk Level": "Low",
            "Threshold Chart": "Green: <5%\nYellow: 5% - 10%\nRed: >10%",
            "Control Procedures": "Period over period change for a Fund's Total Effective Leverage. (Total Effective Leverage CY - Total Effective Leverage PY) / Total Effective Leverage PY",
            "Control Value": 0.02, "FS Value": 0.02, "Variance": 0,
            "BPS Impact": 116.87, "Auto / Manual": "Automated",
            "Validation Source": "KRI Validations", "Validation Type": "KRI Validations",
            "Control Draft Number": "null.1",
            "KRI Variable Key1": "Py Net Assets", "KRI Variable Value1": "18,17,515.00",
            "KRI Variable Key2": "Cy Reverse Repos", "KRI Variable Value2": "9,500.00",
            "KRI Variable Key3": "Cy Credit Default Swaps", "KRI Variable Value3": "51,800.00",
            "KRI Variable Key4": "Cy Net Assets", "KRI Variable Value4": "17,14,756.00",
            "KRI Variable Key5": "Cy Line Of Credit", "KRI Variable Value5": 0
        }
        # Note: India has no KRI validations
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
    
    def assert_in(self, item, container, description: str):
        if item in container:
            self.passed += 1
            self.assertions.append(("PASS", description, None))
        else:
            self.failed += 1
            self.assertions.append(("FAIL", description, f"{item} not found in container"))
    
    def print_summary(self):
        print("\n" + "=" * 80)
        print("QA VALIDATION SUMMARY")
        print("=" * 80)
        print(f"\nTotal Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        
        if self.failed > 0:
            print("\nFailed Tests:")
            for status, desc, error in self.assertions:
                if status == "FAIL":
                    print(f"  ❌ {desc}")
                    print(f"     {error}")
        else:
            print("\n✅ ALL TESTS PASSED!")


def run_qa_tests():
    """Run comprehensive QA tests."""
    runner = TestRunner()
    test_data = get_test_data()
    
    # Create transformer and load data
    transformer = ExcelToJSONTransformer()
    transformer.load_cards(test_data["cards"])
    transformer.load_funds(test_data["funds"])
    transformer.load_validations_trimmed(test_data["validations_trimmed"])
    transformer.load_validations_kri(test_data["validations_kri"])
    
    # Transform all cards
    all_outputs = transformer.transform_all_cards()
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE QA VALIDATION - MULTI-CARD EXCEL TO JSON FRAMEWORK")
    print("=" * 80)
    
    # =========================================================================
    # TEST 1: Utility Functions
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 1: UTILITY FUNCTIONS")
    print("=" * 80)
    
    # Test clean_text
    runner.assert_equal(clean_text("Hello_x000D_ World"), "Hello World", "clean_text removes _x000D_")
    runner.assert_equal(clean_text("  Multiple   Spaces  "), "Multiple Spaces", "clean_text normalizes spaces")
    
    # Test parse_number
    runner.assert_equal(parse_number("7,98,606.00"), 798606.0, "parse_number handles Indian format")
    runner.assert_equal(parse_number("--"), None, "parse_number handles -- as None")
    
    # Test transform_threshold_chart_to_json
    threshold = transform_threshold_chart_to_json("Green: <5%\nYellow: 5% - 7%\nRed: >7%")
    runner.assert_in('"High": ">7%"', threshold, "threshold transform: High value")
    runner.assert_in('"Low": "<5%"', threshold, "threshold transform: Low value")
    runner.assert_in('"Medium": ">=5% and <=7%"', threshold, "threshold transform: Medium range")
    
    # Test file name generation
    runner.assert_equal(
        generate_file_name_from_card("12/31/2024 Canada Annual"),
        "2024-12-31CanadaAnnual.json",
        "File name generation for Canada"
    )
    runner.assert_equal(
        generate_file_name_from_card("12/31/2025 America Annual"),
        "2025-12-31AmericaAnnual.json",
        "File name generation for America"
    )
    
    # =========================================================================
    # TEST 2: Multi-Card Processing
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 2: MULTI-CARD PROCESSING")
    print("=" * 80)
    
    runner.assert_equal(len(all_outputs), 3, "Three cards processed")
    runner.assert_in("12/31/2024 Canada Annual", all_outputs, "Canada card in outputs")
    runner.assert_in("12/31/2025 America Annual", all_outputs, "America card in outputs")
    runner.assert_in("12/31/2025 India Annual", all_outputs, "India card in outputs")
    
    # =========================================================================
    # TEST 3: Canada Card Output
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 3: CANADA CARD OUTPUT")
    print("=" * 80)
    
    canada_outputs = all_outputs["12/31/2024 Canada Annual"]
    canada_json1 = json.loads(canada_outputs["json1"])
    canada_json2 = json.loads(canada_outputs["json2"])
    canada_json3 = json.loads(canada_outputs["json3"])
    canada_json4 = json.loads(canada_outputs["json4"])
    canada_json5 = json.loads(canada_outputs["json5"])
    
    # JSON 1 tests
    runner.assert_equal(
        canada_json1["data"]["getValidations"]["rowCount"], 4,
        "Canada JSON1: 4 validations (1 TRIMMED + 3 KRI)"
    )
    
    validations = canada_json1["data"]["getValidations"]["validations"]
    
    # Check TRIMMED validation
    trimmed_val = [v for v in validations if v["statementType"] == "SCF"][0]
    runner.assert_equal(trimmed_val["trust"], "Canada", "Canada TRIMMED: trust is Canada")
    runner.assert_equal(trimmed_val["fundCode"], "CAN3", "Canada TRIMMED: fundCode is CAN3")
    runner.assert_equal(trimmed_val["group"], "A", "Canada TRIMMED: group is A")
    runner.assert_equal(trimmed_val["priority"], "Material", "Canada TRIMMED: priority is Material")
    runner.assert_equal(trimmed_val["validationId"], "1001", "Canada TRIMMED: validationId is 1001")
    runner.assert_equal(trimmed_val["isFinalDraft"], False, "Canada TRIMMED: isFinalDraft is boolean False")
    runner.assert_equal(trimmed_val["thresholdPercent"], "", "Canada TRIMMED: thresholdPercent cleaned from --")
    
    # Check KRI validations
    kri_vals = [v for v in validations if v["statementType"] == "KRI"]
    runner.assert_equal(len(kri_vals), 3, "Canada has 3 KRI validations")
    
    interest_val = [v for v in kri_vals if "Interest" in v["validation"]][0]
    runner.assert_equal(interest_val["validationId"], "999991", "Interest Expense validationId is 999991")
    runner.assert_equal(interest_val["fundCode"], "CAN2", "Interest Expense fundCode is CAN2")
    
    # JSON 2 tests
    runner.assert_equal(len(canada_json2["data"]["kriDetails"]), 3, "Canada JSON2: 3 KRI details")
    
    kri1 = canada_json2["data"]["kriDetails"][0]
    runner.assert_equal(kri1["kriId"], "KRI_1", "Canada KRI 1: kriId is KRI_1")
    runner.assert_equal(kri1["kriName"], "Interest Expense versus Average Borrowings", "Canada KRI 1 name")
    runner.assert_equal(kri1["fundDetails"][0]["risk"], "High", "Canada KRI 1 risk is High")
    
    kri2 = canada_json2["data"]["kriDetails"][1]
    runner.assert_equal(kri2["kriId"], "KRI_2", "Canada KRI 2: kriId is KRI_2")
    runner.assert_equal(kri2["fundDetails"][0]["risk"], "Medium", "Canada KRI 2 risk is Medium")
    
    kri3 = canada_json2["data"]["kriDetails"][2]
    runner.assert_equal(kri3["kriId"], "KRI_3", "Canada KRI 3: kriId is KRI_3")
    runner.assert_equal(kri3["fundDetails"][0]["risk"], "Low", "Canada KRI 3 risk is Low")
    
    # JSON 3 tests - Fund filtering by Trust
    fund_counts = canada_json3["data"]["fundKriStatusCount"]
    runner.assert_equal(len(fund_counts), 3, "Canada JSON3: 3 funds (Canada trust only)")
    
    fund_codes = [f["fundCode"] for f in fund_counts]
    runner.assert_in("CAN1", fund_codes, "Canada JSON3 has CAN1")
    runner.assert_in("CAN2", fund_codes, "Canada JSON3 has CAN2")
    runner.assert_in("CAN3", fund_codes, "Canada JSON3 has CAN3")
    runner.assert_true("AM1" not in fund_codes, "Canada JSON3 does NOT have AM1")
    
    can1_fund = [f for f in fund_counts if f["fundCode"] == "CAN1"][0]
    runner.assert_equal(can1_fund["kriTotalCount"], "3", "CAN1 kriTotalCount is 3")
    runner.assert_equal(can1_fund["kriStatusCount"], "0", "CAN1 kriStatusCount is 0 (no KRIs for this fund)")
    
    can2_fund = [f for f in fund_counts if f["fundCode"] == "CAN2"][0]
    runner.assert_equal(can2_fund["kriStatusCount"], "2", "CAN2 kriStatusCount is 2")
    
    # JSON 3 kriFilter
    kri_filter = canada_json3["data"]["kriFilter"]
    runner.assert_equal(len(kri_filter), 3, "Canada kriFilter has 3 KRIs")
    runner.assert_equal(kri_filter[0]["kriId"], "KRI_1", "Canada kriFilter[0] is KRI_1")
    runner.assert_equal(kri_filter[1]["kriId"], "KRI_2", "Canada kriFilter[1] is KRI_2")
    runner.assert_equal(kri_filter[2]["kriId"], "KRI_3", "Canada kriFilter[2] is KRI_3")
    
    # JSON 4 tests
    runner.assert_equal(canada_json4["data"][0]["kriTotalCount"], "3", "Canada JSON4 kriTotalCount is 3")
    runner.assert_equal(canada_json4["data"][0]["kriStatusCount"], "3", "Canada JSON4 kriStatusCount is 3")
    
    # JSON 5 tests
    runner.assert_equal(len(canada_json5["kriDetails"]), 3, "Canada JSON5 has 3 KRI details")
    
    # =========================================================================
    # TEST 4: America Card Output
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 4: AMERICA CARD OUTPUT")
    print("=" * 80)
    
    america_outputs = all_outputs["12/31/2025 America Annual"]
    america_json1 = json.loads(america_outputs["json1"])
    america_json2 = json.loads(america_outputs["json2"])
    america_json3 = json.loads(america_outputs["json3"])
    america_json5 = json.loads(america_outputs["json5"])
    
    # JSON 1 tests
    runner.assert_equal(
        america_json1["data"]["getValidations"]["rowCount"], 3,
        "America JSON1: 3 validations (1 TRIMMED + 2 KRI)"
    )
    
    validations = america_json1["data"]["getValidations"]["validations"]
    
    # Check group values for America funds
    am2_val = [v for v in validations if v["fundCode"] == "AM2"][0]
    runner.assert_equal(am2_val["group"], "B", "AM2 group is B")
    runner.assert_equal(am2_val["trust"], "America", "AM2 trust is America")
    
    am3_val = [v for v in validations if v["fundCode"] == "AM3" and v["statementType"] == "SCF"][0]
    runner.assert_equal(am3_val["group"], "C", "AM3 group is C")
    
    # JSON 2 tests - America only has 2 KRIs (no Defaulted Securities)
    runner.assert_equal(len(america_json2["data"]["kriDetails"]), 2, "America JSON2: 2 KRI details")
    
    kri_names = [k["kriName"] for k in america_json2["data"]["kriDetails"]]
    runner.assert_in("Interest Expense versus Average Borrowings", kri_names, "America has Interest Expense KRI")
    runner.assert_in("Effective Leverage: Year Over Year Change", kri_names, "America has Effective Leverage KRI")
    runner.assert_true("Defaulted Securities Review" not in kri_names, "America does NOT have Defaulted Securities")
    
    # Check KRI IDs are globally consistent
    am_kri1 = [k for k in america_json2["data"]["kriDetails"] if "Interest" in k["kriName"]][0]
    runner.assert_equal(am_kri1["kriId"], "KRI_1", "America Interest Expense has global KRI_1")
    
    am_kri3 = [k for k in america_json2["data"]["kriDetails"] if "Leverage" in k["kriName"]][0]
    runner.assert_equal(am_kri3["kriId"], "KRI_3", "America Effective Leverage has global KRI_3")
    
    # JSON 3 tests - Fund filtering by Trust
    fund_counts = america_json3["data"]["fundKriStatusCount"]
    runner.assert_equal(len(fund_counts), 3, "America JSON3: 3 funds (America trust only)")
    
    fund_codes = [f["fundCode"] for f in fund_counts]
    runner.assert_in("AM1", fund_codes, "America JSON3 has AM1")
    runner.assert_in("AM2", fund_codes, "America JSON3 has AM2")
    runner.assert_in("AM3", fund_codes, "America JSON3 has AM3")
    runner.assert_true("CAN1" not in fund_codes, "America JSON3 does NOT have CAN1")
    
    # JSON 3 kriFilter - only 2 KRIs for America
    kri_filter = america_json3["data"]["kriFilter"]
    runner.assert_equal(len(kri_filter), 2, "America kriFilter has 2 KRIs")
    
    kri_ids = [k["kriId"] for k in kri_filter]
    runner.assert_in("KRI_1", kri_ids, "America kriFilter has KRI_1")
    runner.assert_in("KRI_3", kri_ids, "America kriFilter has KRI_3")
    runner.assert_true("KRI_2" not in kri_ids, "America kriFilter does NOT have KRI_2")
    
    # JSON 5 tests
    runner.assert_equal(len(america_json5["kriDetails"]), 2, "America JSON5 has 2 KRI details")
    
    # =========================================================================
    # TEST 5: India Card Output
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 5: INDIA CARD OUTPUT")
    print("=" * 80)
    
    india_outputs = all_outputs["12/31/2025 India Annual"]
    india_json1 = json.loads(india_outputs["json1"])
    india_json3 = json.loads(india_outputs["json3"])
    
    # JSON 1 tests - India has only 1 TRIMMED validation, no KRI
    runner.assert_equal(
        india_json1["data"]["getValidations"]["rowCount"], 1,
        "India JSON1: 1 validation (TRIMMED only, no KRI)"
    )
    
    validations = india_json1["data"]["getValidations"]["validations"]
    runner.assert_equal(validations[0]["trust"], "India", "India validation trust is India")
    runner.assert_equal(validations[0]["fundCode"], "IND3", "India validation fundCode is IND3")
    runner.assert_equal(validations[0]["group"], "F", "IND3 group is F")
    
    # JSON 3 tests - Fund filtering by Trust
    fund_counts = india_json3["data"]["fundKriStatusCount"]
    runner.assert_equal(len(fund_counts), 3, "India JSON3: 3 funds (India trust only)")
    
    fund_codes = [f["fundCode"] for f in fund_counts]
    runner.assert_in("IND1", fund_codes, "India JSON3 has IND1")
    runner.assert_in("IND2", fund_codes, "India JSON3 has IND2")
    runner.assert_in("IND3", fund_codes, "India JSON3 has IND3")
    
    # All funds have 0 KRI count
    for fund in fund_counts:
        runner.assert_equal(fund["kriStatusCount"], "0", f"{fund['fundCode']} kriStatusCount is 0")
    
    # =========================================================================
    # TEST 6: Global KRI ID Consistency
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 6: GLOBAL KRI ID CONSISTENCY")
    print("=" * 80)
    
    # Verify same KRI name has same ID across cards
    canada_interest = [k for k in canada_json2["data"]["kriDetails"] if "Interest" in k["kriName"]][0]
    america_interest = [k for k in america_json2["data"]["kriDetails"] if "Interest" in k["kriName"]][0]
    runner.assert_equal(
        canada_interest["kriId"], america_interest["kriId"],
        "Interest Expense has same KRI ID in Canada and America"
    )
    
    canada_leverage = [k for k in canada_json2["data"]["kriDetails"] if "Leverage" in k["kriName"]][0]
    america_leverage = [k for k in america_json2["data"]["kriDetails"] if "Leverage" in k["kriName"]][0]
    runner.assert_equal(
        canada_leverage["kriId"], america_leverage["kriId"],
        "Effective Leverage has same KRI ID in Canada and America"
    )
    
    # =========================================================================
    # TEST 7: File Name Generation
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 7: FILE NAME GENERATION")
    print("=" * 80)
    
    canada_files = get_output_file_names("12/31/2024 Canada Annual")
    runner.assert_equal(canada_files["json1"], "2024-12-31CanadaAnnual.json", "Canada JSON1 filename")
    runner.assert_equal(canada_files["json2"], "2024-12-31CanadaAnnualkri.json", "Canada JSON2 filename")
    runner.assert_equal(canada_files["json3"], "2024-12-31CanadaAnnualkri-fund.json", "Canada JSON3 filename")
    runner.assert_equal(canada_files["json4"], "2024-12-31CanadaAnnualstrategy.json", "Canada JSON4 filename")
    runner.assert_equal(canada_files["json5"], "2024-12-31CanadaAnnualkri-simple.json", "Canada JSON5 filename")
    
    america_files = get_output_file_names("12/31/2025 America Annual")
    runner.assert_equal(america_files["json1"], "2025-12-31AmericaAnnual.json", "America JSON1 filename")
    
    # =========================================================================
    # Print Summary
    # =========================================================================
    runner.print_summary()
    
    return runner.failed == 0


if __name__ == "__main__":
    success = run_qa_tests()
    exit(0 if success else 1)
