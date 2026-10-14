"""In-memory SQLite execution and query plan analysis sandbox.

Provides a safe execution environment for testing queries, inspecting execution
plans (EXPLAIN QUERY PLAN), and verifying fixes with real database execution.
"""

import time
import sqlite3
from typing import Optional, Tuple, Dict, Any, List
from .models import SandboxExecutionResult, ExecutionPlanInfo


class SQLSandbox:
    """A safe, isolated in-memory database sandbox for query verification."""

    def __init__(self, schema_ddl: Optional[str] = None, seed_data_sql: Optional[str] = None):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._initialize(schema_ddl, seed_data_sql)

    def _initialize(self, schema_ddl: Optional[str], seed_data_sql: Optional[str]):
        cur = self.conn.cursor()
        if schema_ddl:
            try:
                cur.executescript(schema_ddl)
            except sqlite3.Error as e:
                # Log schema error if DDL was invalid
                pass
        if seed_data_sql:
            try:
                cur.executescript(seed_data_sql)
            except sqlite3.Error:
                pass
        self.conn.commit()

    def execute_and_explain(self, query: str) -> SandboxExecutionResult:
        """Executes a query, measures timing, captures rows, and inspects EXPLAIN QUERY PLAN."""
        clean_q = query.strip().rstrip(";")
        if not clean_q:
            return SandboxExecutionResult(success=False, error_message="Empty query provided.")

        result = SandboxExecutionResult(success=False)
        cur = self.conn.cursor()

        # Step 1: EXPLAIN QUERY PLAN
        try:
            cur.execute(f"EXPLAIN QUERY PLAN {clean_q}")
            plan_rows = cur.fetchall()
            steps = []
            has_scan = False
            has_temp_btree = False

            for row in plan_rows:
                # SQLite explain plan row: (id, parent, notused, detail)
                detail = row[3] if len(row) > 3 else str(row)
                steps.append(str(detail))
                detail_upper = str(detail).upper()
                if "SCAN " in detail_upper:
                    has_scan = True
                if "TEMP B-TREE" in detail_upper:
                    has_temp_btree = True

            raw_plan_text = "\n".join(f"• {s}" for s in steps) if steps else "No query plan generated."
            cost_notes = []
            if has_scan:
                cost_notes.append("Detected FULL TABLE SCAN on one or more tables.")
            if has_temp_btree:
                cost_notes.append("Detected in-memory TEMP B-TREE sort/group.")
            if not has_scan and not has_temp_btree:
                cost_notes.append("Efficient execution using indexed search.")

            result.plan = ExecutionPlanInfo(
                engine="SQLite In-Memory Engine",
                raw_plan=raw_plan_text,
                steps=steps,
                has_full_table_scan=has_scan,
                has_temp_b_tree=has_temp_btree,
                cost_notes=" ".join(cost_notes)
            )
        except sqlite3.Error as e:
            # Query might have a syntax error or missing table
            result.error_message = f"Query Plan Error: {str(e)}"
            return result

        # Step 2: Live Execution
        start_t = time.perf_counter()
        try:
            cur.execute(clean_q)
            rows = cur.fetchall()
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            result.success = True
            result.execution_time_ms = round(elapsed_ms, 2)
            result.row_count = len(rows)

            if cur.description:
                result.columns = [d[0] for d in cur.description]
                # Keep up to 10 sample rows for display
                sample = []
                for r in rows[:10]:
                    sample.append(dict(r))
                result.sample_rows = sample
            else:
                result.columns = []
                result.sample_rows = []

        except sqlite3.Error as e:
            result.success = False
            result.error_message = f"Execution Error: {str(e)}"

        return result

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
