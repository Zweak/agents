"""Static SQL Analyzer and Anti-Pattern Linter.

Uses AST parsing and lexical analysis to detect syntax anti-patterns,
non-SARGable predicates, Cartesian products, and schema traps before query execution.
"""

import re
from typing import List, Tuple
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Comparison
from sqlparse.tokens import Keyword, DML, Whitespace

from .models import DetectedIssue, IssueType, IssueSeverity


class SQLStaticAnalyzer:
    """Performs deterministic static analysis on SQL queries."""

    @classmethod
    def analyze(cls, query: str, schema_ddl: str = "") -> List[DetectedIssue]:
        issues: List[DetectedIssue] = []
        clean_q = query.strip()
        if not clean_q:
            return issues

        # 1. Check for SELECT *
        issues.extend(cls._check_select_star(clean_q))

        # 2. Check for Non-SARGable WHERE clauses
        issues.extend(cls._check_non_sargable(clean_q))

        # 3. Check for Cartesian / Comma joins
        issues.extend(cls._check_comma_joins(clean_q))

        # 4. Check for dangerous NOT IN (subquery)
        issues.extend(cls._check_not_in_subquery(clean_q))

        # 5. Check for Leading Wildcards
        issues.extend(cls._check_leading_wildcard(clean_q))

        # 6. Check for LIMIT/OFFSET without ORDER BY
        issues.extend(cls._check_pagination_without_order_by(clean_q))

        # 7. Check for HAVING without aggregate or misplaced filters
        issues.extend(cls._check_having_clause(clean_q))

        # 8. Check for GROUP BY traps
        issues.extend(cls._check_group_by_issues(clean_q))

        # 9. Check for UNION vs UNION ALL
        issues.extend(cls._check_union_all(clean_q))

        return issues

    @classmethod
    def _check_select_star(cls, query: str) -> List[DetectedIssue]:
        issues = []
        # Match SELECT * or SELECT table.*
        if re.search(r"\bSELECT\s+(DISTINCT\s+)?(\w+\.)?\*\b", query, re.IGNORECASE):
            issues.append(
                DetectedIssue(
                    issue_type=IssueType.PERFORMANCE_BOTTLENECK,
                    severity=IssueSeverity.MEDIUM,
                    summary="Anti-Pattern: Use of wildcard 'SELECT *'",
                    detail=(
                        "'SELECT *' retrieves all columns across the table or joined tables. "
                        "This increases network I/O, prevents database engines from utilizing "
                        "index-only (covering) scans, and can break downstream code when tables change."
                    ),
                    recommendation="Explicitly enumerate only the columns required by the application."
                )
            )
        return issues

    @classmethod
    def _check_non_sargable(cls, query: str) -> List[DetectedIssue]:
        issues = []
        # Functions wrapping columns in WHERE conditions: DATE(col), YEAR(col), UPPER(col), LOWER(col), SUBSTRING(col)
        patterns = [
            (
                r"\bWHERE\b.*?\b(DATE|YEAR|MONTH|DAY|HOUR|TO_CHAR|TRUNC)\s*\(\s*([a-zA-Z0-9_\.]+)\s*\)\s*(=|>|<|>=|<=|BETWEEN)",
                "Date/Time function wrapping column in WHERE clause"
            ),
            (
                r"\bWHERE\b.*?\b(UPPER|LOWER)\s*\(\s*([a-zA-Z0-9_\.]+)\s*\)\s*(=|LIKE)",
                "Case conversion function (UPPER/LOWER) wrapping column in WHERE clause"
            ),
            (
                r"\bWHERE\b.*?([a-zA-Z0-9_\.]+)\s*[\+\-\*\/]\s*\d+\s*(=|>|<|>=|<=)",
                "Arithmetic operation on column expression in WHERE clause"
            )
        ]

        for pat, desc in patterns:
            match = re.search(pat, query, re.IGNORECASE | re.DOTALL)
            if match:
                col_name = match.group(2) if len(match.groups()) >= 2 else "column"
                issues.append(
                    DetectedIssue(
                        issue_type=IssueType.PERFORMANCE_BOTTLENECK,
                        severity=IssueSeverity.HIGH,
                        summary=f"Non-SARGable Predicate: {desc}",
                        detail=(
                            f"Applying functions or arithmetic directly to indexed column '{col_name}' "
                            f"invalidates B-tree indexes, forcing the database engine into a full table scan. "
                            f"The query engine must evaluate the function on every single row."
                        ),
                        recommendation=(
                            "Rewrite the predicate to isolate the column (e.g. use a range comparison: "
                            "`col >= '2025-01-01' AND col < '2025-01-02'` instead of `DATE(col) = '2025-01-01'`)."
                        )
                    )
                )
                break
        return issues

    @classmethod
    def _check_comma_joins(cls, query: str) -> List[DetectedIssue]:
        issues = []
        # Detect legacy comma joins: FROM table1, table2
        # Look for FROM word followed by comma and another word before WHERE/ORDER/GROUP/LIMIT
        match = re.search(r"\bFROM\s+([a-zA-Z0-9_]+(\s+AS)?(\s+[a-zA-Z0-9_]+)?)\s*,\s*([a-zA-Z0-9_]+)", query, re.IGNORECASE)
        if match:
            # Check if there is an explicit WHERE clause joining them
            has_where = bool(re.search(r"\bWHERE\b", query, re.IGNORECASE))
            severity = IssueSeverity.CRITICAL if not has_where else IssueSeverity.MEDIUM
            issues.append(
                DetectedIssue(
                    issue_type=IssueType.SEMANTIC_ERROR if not has_where else IssueType.BEST_PRACTICE,
                    severity=severity,
                    summary="Legacy Comma Join / Potential Cartesian Product",
                    detail=(
                        "Using comma-separated table lists in the FROM clause (`FROM table_a, table_b`) "
                        "is error-prone and can easily cause an unintended Cartesian product (CROSS JOIN), "
                        "massively duplicating rows and degrading memory/CPU."
                    ),
                    recommendation="Refactor into modern ANSI explicit JOINs (`INNER JOIN ... ON ...`)."
                )
            )
        return issues

    @classmethod
    def _check_not_in_subquery(cls, query: str) -> List[DetectedIssue]:
        issues = []
        if re.search(r"\bNOT\s+IN\s*\(\s*SELECT\b", query, re.IGNORECASE):
            issues.append(
                DetectedIssue(
                    issue_type=IssueType.SEMANTIC_ERROR,
                    severity=IssueSeverity.HIGH,
                    summary="Dangerous 'NOT IN (SELECT ...)' Three-Valued Logic Trap",
                    detail=(
                        "In SQL, if the subquery returns even a single NULL value, `NOT IN` evaluates to UNKNOWN (false) "
                        "for all candidate rows, causing the query to unexpectedly return 0 rows. "
                        "Additionally, `NOT IN` cannot be optimized as effectively as anti-joins."
                    ),
                    recommendation="Rewrite using `NOT EXISTS (SELECT 1 FROM ... WHERE ...)` or `LEFT JOIN ... WHERE right_table.id IS NULL`."
                )
            )
        return issues

    @classmethod
    def _check_leading_wildcard(cls, query: str) -> List[DetectedIssue]:
        issues = []
        if re.search(r"\bLIKE\s+['\"][%_]", query, re.IGNORECASE):
            issues.append(
                DetectedIssue(
                    issue_type=IssueType.PERFORMANCE_BOTTLENECK,
                    severity=IssueSeverity.HIGH,
                    summary="Leading Wildcard in LIKE clause",
                    detail=(
                        "Predicates like `LIKE '%term'` or `LIKE '%term%'` cannot utilize standard B-Tree indexes. "
                        "The database must scan every single row and perform string substring matching."
                    ),
                    recommendation="If suffix matching is needed, consider full-text search (FTS), trigram indexes (pg_trgm in PostgreSQL), or prefix searches (`'term%'`)."
                )
            )
        return issues

    @classmethod
    def _check_pagination_without_order_by(cls, query: str) -> List[DetectedIssue]:
        issues = []
        has_limit = bool(re.search(r"\b(LIMIT|OFFSET)\b", query, re.IGNORECASE))
        has_order_by = bool(re.search(r"\bORDER\s+BY\b", query, re.IGNORECASE))
        if has_limit and not has_order_by:
            issues.append(
                DetectedIssue(
                    issue_type=IssueType.SEMANTIC_ERROR,
                    severity=IssueSeverity.MEDIUM,
                    summary="Pagination (LIMIT / OFFSET) without deterministic ORDER BY",
                    detail=(
                        "Tables in relational databases have no inherent ordering. Calling `LIMIT` without an `ORDER BY` "
                        "clause yields non-deterministic results: subsequent requests or database restart can return different subsets."
                    ),
                    recommendation="Add an explicit, deterministic `ORDER BY` column (e.g. primary key or created_at)."
                )
            )
        return issues

    @classmethod
    def _check_having_clause(cls, query: str) -> List[DetectedIssue]:
        issues = []
        having_match = re.search(r"\bHAVING\b(.*?)(GROUP\s+BY|ORDER\s+BY|LIMIT|$)", query, re.IGNORECASE | re.DOTALL)
        if having_match:
            having_body = having_match.group(1)
            # If having does not contain an aggregate function (COUNT, SUM, AVG, MIN, MAX)
            if not re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", having_body, re.IGNORECASE):
                issues.append(
                    DetectedIssue(
                        issue_type=IssueType.PERFORMANCE_BOTTLENECK,
                        severity=IssueSeverity.MEDIUM,
                        summary="Non-aggregate filter inside HAVING clause",
                        detail=(
                            "The `HAVING` clause filters rows AFTER grouping and aggregation. Filtering non-aggregate "
                            "columns in `HAVING` forces the engine to aggregate unwanted rows."
                        ),
                        recommendation="Move non-aggregate conditions into the `WHERE` clause so rows are pruned before aggregation."
                    )
                )
        return issues

    @classmethod
    def _check_group_by_issues(cls, query: str) -> List[DetectedIssue]:
        issues = []
        # If there's an aggregate in SELECT but no GROUP BY, and other non-aggregate columns are present
        has_group_by = bool(re.search(r"\bGROUP\s+BY\b", query, re.IGNORECASE))
        select_match = re.search(r"\bSELECT\b(.*?)\bFROM\b", query, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_cols = select_match.group(1)
            has_aggregate = bool(re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", select_cols, re.IGNORECASE))
            # Check if there are non-aggregate identifiers
            # If aggregate is present but no GROUP BY, and there is more than just the aggregate:
            if has_aggregate and not has_group_by:
                # E.g. SELECT department_id, COUNT(*) FROM employees
                # If there are commas in select_cols
                if "," in select_cols:
                    issues.append(
                        DetectedIssue(
                            issue_type=IssueType.SYNTAX_ERROR,
                            severity=IssueSeverity.CRITICAL,
                            summary="Missing GROUP BY clause for aggregate query",
                            detail=(
                                "Query contains both scalar columns and aggregate functions (e.g. `COUNT()`, `SUM()`) "
                                "without a `GROUP BY` clause. Strict SQL dialects (PostgreSQL, SQL Server, MySQL ANSI mode) "
                                "will reject this with an error like 'column must appear in the GROUP BY clause'."
                            ),
                            recommendation="Add `GROUP BY` containing all unaggregated columns listed in the `SELECT` clause."
                        )
                    )
        return issues

    @classmethod
    def _check_union_all(cls, query: str) -> List[DetectedIssue]:
        issues = []
        # If UNION without ALL
        if re.search(r"\bUNION\b(?!\s+ALL\b)", query, re.IGNORECASE):
            issues.append(
                DetectedIssue(
                    issue_type=IssueType.PERFORMANCE_BOTTLENECK,
                    severity=IssueSeverity.LOW,
                    summary="Use of 'UNION' instead of 'UNION ALL'",
                    detail=(
                        "`UNION` executes an expensive DISTINCT sort/hash deduplication across the entire result set. "
                        "If rows are already known to be unique or duplicates are acceptable, `UNION ALL` is significantly faster."
                    ),
                    recommendation="Use `UNION ALL` unless deduplication is explicitly required."
                )
            )
        return issues
