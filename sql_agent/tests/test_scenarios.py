"""Automated validation tests for SQL Debugging & Optimization Agent."""

import unittest
from agent.core import SQLAgent
from agent.presets import PRESET_SCENARIOS


class TestSQLAgent(unittest.TestCase):
    def setUp(self):
        self.agent = SQLAgent(provider="heuristic")

    def test_scenario_1_group_by_fix(self):
        s1 = PRESET_SCENARIOS[0]
        res = self.agent.diagnose_and_optimize(
            query=s1["query"],
            dialect=s1["dialect"],
            error_message=s1["error_message"],
            business_requirement=s1["business_requirement"],
            schema_ddl=s1["schema_ddl"],
            seed_data=s1["seed_data"]
        )
        self.assertNotIn("first_name", res.corrected_query)
        self.assertIn("department_name", res.corrected_query)
        self.assertTrue(res.execution_verified)
        self.assertIsNotNone(res.corrected_execution)
        self.assertTrue(res.corrected_execution.success)

    def test_scenario_2_cartesian_join(self):
        s2 = PRESET_SCENARIOS[1]
        res = self.agent.diagnose_and_optimize(
            query=s2["query"],
            dialect=s2["dialect"],
            error_message=s2["error_message"],
            business_requirement=s2["business_requirement"],
            schema_ddl=s2["schema_ddl"],
            seed_data=s2["seed_data"]
        )
        self.assertIn("INNER JOIN", res.corrected_query)
        self.assertTrue(res.execution_verified)

    def test_scenario_3_non_sargable(self):
        s3 = PRESET_SCENARIOS[2]
        res = self.agent.diagnose_and_optimize(
            query=s3["query"],
            dialect=s3["dialect"],
            error_message=s3["error_message"],
            business_requirement=s3["business_requirement"],
            schema_ddl=s3["schema_ddl"],
            seed_data=s3["seed_data"]
        )
        self.assertIn(">=", res.corrected_query)
        self.assertTrue(res.execution_verified)

    def test_scenario_4_not_in_null_trap(self):
        s4 = PRESET_SCENARIOS[3]
        res = self.agent.diagnose_and_optimize(
            query=s4["query"],
            dialect=s4["dialect"],
            error_message=s4["error_message"],
            business_requirement=s4["business_requirement"],
            schema_ddl=s4["schema_ddl"],
            seed_data=s4["seed_data"]
        )
        self.assertIn("NOT EXISTS", res.corrected_query)
        self.assertTrue(res.execution_verified)
        # Check that customer with ID 4 (SilentBuyer) is returned in corrected execution!
        names = [r["name"] for r in res.corrected_execution.sample_rows]
        self.assertIn("SilentBuyer", names)

    def test_scenario_5_window_function(self):
        s5 = PRESET_SCENARIOS[4]
        res = self.agent.diagnose_and_optimize(
            query=s5["query"],
            dialect=s5["dialect"],
            error_message=s5["error_message"],
            business_requirement=s5["business_requirement"],
            schema_ddl=s5["schema_ddl"],
            seed_data=s5["seed_data"]
        )
        self.assertIn("ROW_NUMBER()", res.corrected_query)
        self.assertTrue(res.execution_verified)


if __name__ == "__main__":
    unittest.main()
