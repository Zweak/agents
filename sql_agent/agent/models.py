"""Data models for SQL Debugging & Optimization Agent."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SQLDialect(str, Enum):
    POSTGRESQL = "PostgreSQL"
    MYSQL = "MySQL"
    SQLITE = "SQLite"
    SNOWFLAKE = "Snowflake"
    SQLSERVER = "SQL Server (T-SQL)"
    BIGQUERY = "Google BigQuery"
    GENERIC = "Generic ANSI SQL"


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class IssueType(str, Enum):
    SYNTAX_ERROR = "Syntax Error"
    SEMANTIC_ERROR = "Semantic / Logic Error"
    PERFORMANCE_BOTTLENECK = "Performance Bottleneck"
    SCHEMA_MISMATCH = "Schema Mismatch"
    SECURITY_RISK = "Security / Injection Risk"
    BEST_PRACTICE = "Best Practice / Anti-pattern"


class DetectedIssue(BaseModel):
    issue_type: IssueType
    severity: IssueSeverity
    summary: str
    detail: str
    line_number: Optional[int] = None
    recommendation: str


class IndexRecommendation(BaseModel):
    table_name: str
    columns: List[str]
    index_name: str
    ddl: str
    rationale: str


class ExecutionPlanInfo(BaseModel):
    engine: str = "SQLite Sandbox"
    raw_plan: str
    steps: List[str] = Field(default_factory=list)
    has_full_table_scan: bool = False
    has_temp_b_tree: bool = False
    cost_notes: Optional[str] = None


class SandboxExecutionResult(BaseModel):
    success: bool
    row_count: int = 0
    columns: List[str] = Field(default_factory=list)
    sample_rows: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    plan: Optional[ExecutionPlanInfo] = None


class AnalysisResult(BaseModel):
    original_query: str
    dialect: str = SQLDialect.GENERIC.value
    error_message_input: Optional[str] = None
    business_requirement_input: Optional[str] = None
    schema_context_input: Optional[str] = None

    root_cause: str
    issues: List[DetectedIssue] = Field(default_factory=list)
    corrected_query: str
    diff_unified: str = ""
    explanation: str
    changes_made: List[str] = Field(default_factory=list)
    performance_notes: List[str] = Field(default_factory=list)
    index_recommendations: List[IndexRecommendation] = Field(default_factory=list)

    execution_verified: bool = False
    original_execution: Optional[SandboxExecutionResult] = None
    corrected_execution: Optional[SandboxExecutionResult] = None

    engine_used: str = "Built-in Expert Engine"
    time_taken_seconds: float = 0.0


class OptimizationReport(BaseModel):
    summary: str
    result: AnalysisResult
