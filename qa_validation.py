#!/usr/bin/env python3
"""
Comprehensive QA Validation for Excel to JSON Framework.
Tests multi-card processing, unique IDs across cards, and data integrity.
"""

import json
from typing import Dict, Any, List
from excel_to_json_transformer import (
    ExcelToJSONTransformer,
    clean_text,
    parse_number,
    transform_threshold_chart_to_json,
    generate_file_name_from_card,
    get_output_file_names
)


# =============================================================================
# Test Data - Multi-Card Scenario
# =============================================================================

def get_test_data() -> Dict[str, List[Dict[str, Any]]]:
    """Get test data matching the user's input specification."""
    
    cards_data = [
        {"Card Name": "12/31/2024 Canada Annual", "open_end_close_end": "Canada"},
        {"Card Name": "12/31/2024 America Annual", "open_end_close_end": "America"},
        {"Card Name": "12/31/2025 India Annual", "open_end_close_end": "India"}
    ]
    
    funds_data = [
        {"Trust": "Canada", "Trust_New": "Canada", "Fund ID_New": "CAN1", "Fund Name_New": "Income Strategy Fund", 
         "Group": "H", "Group_New": "A", "Book": "Test Book", "Book_New": "Income Strategy Fund",
         "12/31/2024 Canada Annual": "X"},
        {"Trust": "Canada", "Trust_New": "Canada", "Fund ID_New": "CAN2", "Fund Name_New": "Credit Income Fund", 
         "Group": "H", "Group_New": "A", "Book": "Test Book", "Book_New": "Credit Income Fund",
         "12/31/2024 Canada Annual": "X"},
        {"Trust": "Canada", "Trust_New": "Canada", "Fund ID_New": "CAN3", "Fund Name_New": "International Bond Trust", 
         "Group": "G", "Group_New": "A", "Book": "Test Book", "Book_New": "International Bond Trust",
         "12/31/2024 Canada Annual": "X"},
        {"Trust": "America", "Trust_New": "America", "Fund ID_New": "AM1", "Fund Name_New": "Income Strategy Fund", 
         "Group": "H", "Group_New": "A", "Book": "Test Book", "Book_New": "Income Strategy Fund",
         "12/31/2024 America Annual": "X"},
        {"Trust": "America", "Trust_New": "America", "Fund ID_New": "AM2", "Fund Name_New": "Credit Income Fund", 
         "Group": "H", "Group_New": "B", "Book": "Test Book", "Book_New": "Credit Income Fund",
         "12/31/2024 America Annual": "X"},
        {"Trust": "America", "Trust_New": "America", "Fund ID_New": "AM3", "Fund Name_New": "International Bond Trust", 
         "Group": "G", "Group_New": "C", "Book": "Test Book", "Book_New": "International Bond Trust",
         "12/31/2024 America Annual": "X"},
        {"Trust": "India", "Trust_New": "India", "Fund ID_New": "IND1", "Fund Name_New": "Income Strategy Fund", 
         "Group": "H", "Group_New": "D", "Book": "Test Book", "Book_New": "Income Strategy Fund",
         "12/31/2025 India Annual": "X"},
        {"Trust": "India", "Trust_New": "India", "Fund ID_New": "IND2", "Fund Name_New": "Credit Income Fund", 
         "Group": "H", "Group_New": "E", "Book": "Test Book", "Book_New": "Credit Income Fund",
         "12/31/2025 India Annual": "X"},
        {"Trust": "India", "Trust_New": "India", "Fund ID_New": "IND3", "Fund Name_New": "International Bond Trust", 
         "Group": "G", "Group_New": "F", "Book": "Test Book", "Book_New": "International Bond Trust",
         "12/31/2025 India Annual": "X"}
    ]
    
    validations_trimmed_data = [
        {"Card": "12/31/2024 Canada Annual", "Fund": "CAN3", "Priority": "Material",
         "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Validation": "SCF_admin vs generalledger_adjusted_entries_ey_CANADA",
         "Statement Type": "SCF", "Section": "Net Realized (Gain) Loss",
         "Line Item Description": "Foreign currency transactions",
         "Control Procedures": "SCF_admin vs generalledger_adjusted_entries_ey_CANADA",
         "Control Value": -141, "FS Value": -152, "Variance": 11,
         "BPS Impact": -0.078014184, "Auto / Manual": "Automated",
         "Validation Source": "Recon_Engine", "Validation Type": "AFS - Indicative FS",
         "Control Draft Number": "2.1"},
        {"Card": "12/31/2024 America Annual", "Fund": "AM3", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Failed",
         "Validation": "SCF_admin vs generalledger_adjusted_entries_ey_AMERICA",
         "Statement Type": "SCF", "Section": "Net Realized (Gain) Loss",
         "Line Item Description": "Foreign currency transactions",
         "Control Procedures": "SCF_admin vs generalledger_adjusted_entries_ey_AMERICA",
         "Control Value": -141, "FS Value": -152, "Variance": 11,
         "BPS Impact": -0.078014184, "Auto / Manual": "Automated",
         "Validation Source": "Recon_Engine", "Validation Type": "AFS - Indicative FS",
         "Control Draft Number": "3.1"},
        {"Card": "12/31/2025 India Annual", "Fund": "IND3", "Priority": "Material",
         "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Validation": "SCF_admin vs generalledger_adjusted_entries_ey_India",
         "Statement Type": "SCF", "Section": "Net Realized (Gain) Loss",
         "Line Item Description": "Foreign currency transactions",
         "Control Procedures": "SCF_admin vs generalledger_adjusted_entries_ey_India",
         "Control Value": -141, "FS Value": -152, "Variance": 11,
         "BPS Impact": -0.078014184, "Auto / Manual": "Automated",
         "Validation Source": "Recon_Engine", "Validation Type": "AFS - Indicative FS",
         "Control Draft Number": "4.1"}
    ]
    
    validations_kri_data = [
        # Canada KRI validations - 3 unique names: Interest Expense, Defaulted Securities, Effective Leverage
        {"Card": "12/31/2024 Canada Annual", "Fund": "CAN2", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Validation": "Interest Expense versus Average Borrowings",  # Name #1 -> KRI_1
         "Statement Type": "KRI", "Risk Level": "High",
         "Threshold Chart": "Green: <5%\nYellow: 5% - 7%\nRed: >7%",
         "Control Procedures": "Test control procedure",
         "Control Value": -25.06, "FS Value": -1633, "Variance": -25.06,
         "BPS Impact": 1.53, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations"},
        {"Card": "12/31/2024 Canada Annual", "Fund": "CAN2", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Validation": "Defaulted Securities Review",  # Name #2 -> KRI_2
         "Statement Type": "KRI", "Risk Level": "Medium",
         "Threshold Chart": "Green: <3%\nYellow: 3% - 5%\nRed: >5%",
         "Control Procedures": "Test control procedure",
         "Control Value": 0, "FS Value": 798606, "Variance": 0,
         "BPS Impact": 0, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations"},
        {"Card": "12/31/2024 Canada Annual", "Fund": "CAN3", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Passed",
         "Validation": "Effective Leverage: Year Over Year Change",  # Name #3 -> KRI_3
         "Statement Type": "KRI", "Risk Level": "Low",
         "Threshold Chart": "Green: <5%\nYellow: 5% - 10%\nRed: >10%",
         "Control Procedures": "Test control procedure",
         "Control Value": 0.02, "FS Value": 0.02, "Variance": 0,
         "BPS Impact": 116.87, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations"},
        # America KRI validations - SAME names get SAME IDs (per Issue 1 clarification)
        {"Card": "12/31/2024 America Annual", "Fund": "AM2", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Failed",
         "Validation": "Interest Expense versus Average Borrowings",  # SAME as Name #1 -> KRI_1
         "Statement Type": "KRI", "Risk Level": "High",
         "Threshold Chart": "Green: <5%\nYellow: 5% - 7%\nRed: >7%",
         "Control Procedures": "Test control procedure",
         "Control Value": -25.06, "FS Value": -1633, "Variance": -25.06,
         "BPS Impact": 1.53, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations"},
        {"Card": "12/31/2024 America Annual", "Fund": "AM3", "Priority": "Standard",
         "Workflow Status": "EY L1 Review", "Validation Status": "Failed",
         "Validation": "Effective Leverage: Year Over Year Change",  # SAME as Name #3 -> KRI_3
         "Statement Type": "KRI", "Risk Level": "Low",
         "Threshold Chart": "Green: <5%\nYellow: 5% - 10%\nRed: >10%",
         "Control Procedures": "Test control procedure",
         "Control Value": 0.02, "FS Value": 0.02, "Variance": 0,
         "BPS Impact": 116.87, "Auto / Manual": "Automated",
         "Validation Source": "KRI Validations", "Validation Type": "KRI Validations"}
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
    print("COMPREHENSIVE QA VALIDATION - UNIQUE IDs ACROSS ALL CARDS")
    print("=" * 80)
    
    # =========================================================================
    # TEST 1: KRI IDs Based on Validation NAME (Same name = Same ID)
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 1: KRI IDs BASED ON VALIDATION NAME")
    print("        (Same validation name = Same KRI ID, regardless of card)")
    print("=" * 80)
    
    # Collect all KRI IDs and Validation IDs from all cards
    canada2 = json.loads(all_outputs["12/31/2024 Canada Annual"]["json2"])
    america2 = json.loads(all_outputs["12/31/2024 America Annual"]["json2"])
    
    canada_kri_ids = [kri["kriId"] for kri in canada2["data"]["kriDetails"]]
    canada_val_ids = [kri["fundDetails"][0]["validationId"] for kri in canada2["data"]["kriDetails"]]
    america_kri_ids = [kri["kriId"] for kri in america2["data"]["kriDetails"]]
    america_val_ids = [kri["fundDetails"][0]["validationId"] for kri in america2["data"]["kriDetails"]]
    
    # Canada has 3 unique KRI names
    runner.assert_equal(canada_kri_ids, ["KRI_1", "KRI_2", "KRI_3"], "Canada KRI IDs: 1, 2, 3")
    runner.assert_equal(canada_val_ids, ["999991", "999992", "999993"], "Canada Validation IDs: 999991-93")
    
    # America has 2 KRIs, but SAME names as Canada, so SAME IDs
    runner.assert_equal(america_kri_ids, ["KRI_1", "KRI_3"], "America KRI IDs: 1, 3 (same names as Canada)")
    runner.assert_equal(america_val_ids, ["999991", "999993"], "America Validation IDs match Canada's")
    
    # =========================================================================
    # TEST 2: Canada Card - Correct KRI IDs
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 2: CANADA CARD - KRI IDs 1, 2, 3")
    print("=" * 80)
    
    canada_kris = canada2["data"]["kriDetails"]
    runner.assert_equal(len(canada_kris), 3, "Canada has 3 KRI validations")
    runner.assert_equal(canada_kris[0]["kriId"], "KRI_1", "Canada KRI 1: Interest Expense = KRI_1")
    runner.assert_equal(canada_kris[1]["kriId"], "KRI_2", "Canada KRI 2: Defaulted Securities = KRI_2")
    runner.assert_equal(canada_kris[2]["kriId"], "KRI_3", "Canada KRI 3: Effective Leverage = KRI_3")
    
    runner.assert_equal(canada_kris[0]["fundDetails"][0]["validationId"], "999991", "Canada KRI 1 validationId = 999991")
    runner.assert_equal(canada_kris[1]["fundDetails"][0]["validationId"], "999992", "Canada KRI 2 validationId = 999992")
    runner.assert_equal(canada_kris[2]["fundDetails"][0]["validationId"], "999993", "Canada KRI 3 validationId = 999993")
    
    # =========================================================================
    # TEST 3: America Card - SAME Names = SAME IDs
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 3: AMERICA CARD - KRI IDs 1, 3 (SAME as Canada for same names)")
    print("=" * 80)
    
    america_kris = america2["data"]["kriDetails"]
    runner.assert_equal(len(america_kris), 2, "America has 2 KRI validations")
    runner.assert_equal(america_kris[0]["kriId"], "KRI_1", "America 'Interest Expense' = KRI_1 (SAME as Canada)")
    runner.assert_equal(america_kris[1]["kriId"], "KRI_3", "America 'Effective Leverage' = KRI_3 (SAME as Canada)")
    
    runner.assert_equal(america_kris[0]["fundDetails"][0]["validationId"], "999991", "America KRI validationId = 999991 (SAME)")
    runner.assert_equal(america_kris[1]["fundDetails"][0]["validationId"], "999993", "America KRI validationId = 999993 (SAME)")
    
    # =========================================================================
    # TEST 4: JSON1 - Validation IDs in Combined Output
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 4: JSON1 - VALIDATION IDs (same name = same ID)")
    print("=" * 80)
    
    canada1 = json.loads(all_outputs["12/31/2024 Canada Annual"]["json1"])
    america1 = json.loads(all_outputs["12/31/2024 America Annual"]["json1"])
    
    canada_vals = canada1["data"]["getValidations"]["validations"]
    america_vals = america1["data"]["getValidations"]["validations"]
    
    # Check KRI validation IDs in JSON1
    canada_kri_vals = [v for v in canada_vals if v["statementType"] == "KRI"]
    america_kri_vals = [v for v in america_vals if v["statementType"] == "KRI"]
    
    runner.assert_equal(canada_kri_vals[0]["validationId"], "999991", "Canada JSON1: Interest Expense validationId = 999991")
    runner.assert_equal(canada_kri_vals[1]["validationId"], "999992", "Canada JSON1: Defaulted Securities validationId = 999992")
    runner.assert_equal(canada_kri_vals[2]["validationId"], "999993", "Canada JSON1: Effective Leverage validationId = 999993")
    
    runner.assert_equal(america_kri_vals[0]["validationId"], "999991", "America JSON1: Interest Expense validationId = 999991 (SAME)")
    runner.assert_equal(america_kri_vals[1]["validationId"], "999993", "America JSON1: Effective Leverage validationId = 999993 (SAME)")
    
    # =========================================================================
    # TEST 5: JSON3 - kriFilter with IDs based on name
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 5: JSON3 - KRIFILTER (same name = same ID)")
    print("=" * 80)
    
    canada3 = json.loads(all_outputs["12/31/2024 Canada Annual"]["json3"])
    america3 = json.loads(all_outputs["12/31/2024 America Annual"]["json3"])
    
    canada_filter = canada3["data"]["kriFilter"]
    america_filter = america3["data"]["kriFilter"]
    
    runner.assert_equal(len(canada_filter), 3, "Canada kriFilter has 3 entries")
    runner.assert_equal(canada_filter[0]["kriId"], "KRI_1", "Canada kriFilter[0] = KRI_1")
    runner.assert_equal(canada_filter[1]["kriId"], "KRI_2", "Canada kriFilter[1] = KRI_2")
    runner.assert_equal(canada_filter[2]["kriId"], "KRI_3", "Canada kriFilter[2] = KRI_3")
    
    runner.assert_equal(len(america_filter), 2, "America kriFilter has 2 entries")
    runner.assert_equal(america_filter[0]["kriId"], "KRI_1", "America kriFilter[0] = KRI_1 (SAME as Canada)")
    runner.assert_equal(america_filter[1]["kriId"], "KRI_3", "America kriFilter[1] = KRI_3 (SAME as Canada)")
    
    # =========================================================================
    # TEST 6: JSON5 - Simple KRI Details (same name = same ID)
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 6: JSON5 - SIMPLE KRI DETAILS (same name = same ID)")
    print("=" * 80)
    
    canada5 = json.loads(all_outputs["12/31/2024 Canada Annual"]["json5"])
    america5 = json.loads(all_outputs["12/31/2024 America Annual"]["json5"])
    
    runner.assert_equal(len(canada5["kriDetails"]), 3, "Canada JSON5 has 3 entries")
    runner.assert_equal(canada5["kriDetails"][0]["kriId"], "KRI_1", "Canada JSON5[0] = KRI_1")
    runner.assert_equal(canada5["kriDetails"][2]["kriId"], "KRI_3", "Canada JSON5[2] = KRI_3")
    
    runner.assert_equal(len(america5["kriDetails"]), 2, "America JSON5 has 2 entries")
    runner.assert_equal(america5["kriDetails"][0]["kriId"], "KRI_1", "America JSON5[0] = KRI_1 (SAME)")
    runner.assert_equal(america5["kriDetails"][1]["kriId"], "KRI_3", "America JSON5[1] = KRI_3 (SAME)")
    
    # =========================================================================
    # TEST 7: India - No KRIs
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST 7: INDIA - NO KRI VALIDATIONS")
    print("=" * 80)
    
    india1 = json.loads(all_outputs["12/31/2025 India Annual"]["json1"])
    india2 = json.loads(all_outputs["12/31/2025 India Annual"]["json2"])
    
    runner.assert_equal(india1["data"]["getValidations"]["rowCount"], 1, "India has 1 validation (TRIMMED only)")
    runner.assert_equal(len(india2["data"]["kriDetails"]), 0, "India has 0 KRI details")
    
    # =========================================================================
    # Print Summary
    # =========================================================================
    runner.print_summary()
    
    return runner.failed == 0


if __name__ == "__main__":
    success = run_qa_tests()
    exit(0 if success else 1)
