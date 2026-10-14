"""Main Agent Orchestrator for SQL Debugging & Optimization."""

import time
import os
from typing import Optional
from .models import AnalysisResult, OptimizationReport
from .sandbox import SQLSandbox
from .heuristic_engine import HeuristicSQLEngine
from .llm_engine import LLMSQLEngine


class SQLAgent:
    """Intelligent SQL Debugging, Optimization, and Verification Agent."""

    def __init__(
        self,
        provider: str = "auto",  # 'auto', 'gemini', 'openai', 'heuristic'
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url

    def diagnose_and_optimize(
        self,
        query: str,
        dialect: str = "PostgreSQL",
        error_message: Optional[str] = None,
        business_requirement: Optional[str] = None,
        schema_ddl: Optional[str] = None,
        seed_data: Optional[str] = None,
        verify_in_sandbox: bool = True
    ) -> AnalysisResult:
        """Runs the multi-stage diagnostic, rewrite, and verification agent loop."""
        start_time = time.perf_counter()

        # Phase 1: Determine engine and execute analysis
        result = self._dispatch_analysis(
            query=query,
            dialect=dialect,
            error_message=error_message,
            business_requirement=business_requirement,
            schema_ddl=schema_ddl
        )

        # Phase 2: Live Sandbox Execution & Plan Verification (Tool Use)
        if verify_in_sandbox and (schema_ddl or seed_data):
            try:
                sandbox = SQLSandbox(schema_ddl=schema_ddl, seed_data_sql=seed_data)

                # Test Original Query
                orig_exec = sandbox.execute_and_explain(query)
                result.original_execution = orig_exec

                # Test Corrected Query
                corr_exec = sandbox.execute_and_explain(result.corrected_query)
                result.corrected_execution = corr_exec

                if corr_exec.success:
                    result.execution_verified = True

                sandbox.close()
            except Exception as e:
                # Sandbox execution is best-effort tool verification
                pass

        elapsed = time.perf_counter() - start_time
        result.time_taken_seconds = round(elapsed, 3)

        return result

    def _dispatch_analysis(
        self,
        query: str,
        dialect: str,
        error_message: Optional[str],
        business_requirement: Optional[str],
        schema_ddl: Optional[str]
    ) -> AnalysisResult:
        gemini_key = self.api_key or os.getenv("GEMINI_API_KEY")
        openai_key = self.api_key or os.getenv("OPENAI_API_KEY")

        # Force Heuristic
        if self.provider in ("heuristic", "offline", "builtin"):
            return HeuristicSQLEngine.analyze_and_fix(
                query=query,
                dialect=dialect,
                error_message=error_message,
                business_requirement=business_requirement,
                schema_ddl=schema_ddl
            )

        # Gemini requested
        if self.provider == "gemini" or (self.provider == "auto" and gemini_key):
            try:
                return LLMSQLEngine.analyze_with_gemini(
                    query=query,
                    dialect=dialect,
                    error_message=error_message,
                    business_requirement=business_requirement,
                    schema_ddl=schema_ddl,
                    api_key=gemini_key,
                    model_name=self.model_name or "gemini-2.5-flash"
                )
            except Exception as e:
                # Graceful fallback to heuristic engine if API fails
                res = HeuristicSQLEngine.analyze_and_fix(
                    query=query,
                    dialect=dialect,
                    error_message=error_message,
                    business_requirement=business_requirement,
                    schema_ddl=schema_ddl
                )
                res.engine_used = f"Built-in Expert Engine (Gemini fallback: {str(e)[:60]}...)"
                return res

        # OpenAI requested
        if self.provider == "openai" or (self.provider == "auto" and openai_key):
            try:
                return LLMSQLEngine.analyze_with_openai(
                    query=query,
                    dialect=dialect,
                    error_message=error_message,
                    business_requirement=business_requirement,
                    schema_ddl=schema_ddl,
                    api_key=openai_key,
                    base_url=self.base_url,
                    model_name=self.model_name or "gpt-4o"
                )
            except Exception as e:
                res = HeuristicSQLEngine.analyze_and_fix(
                    query=query,
                    dialect=dialect,
                    error_message=error_message,
                    business_requirement=business_requirement,
                    schema_ddl=schema_ddl
                )
                res.engine_used = f"Built-in Expert Engine (OpenAI fallback: {str(e)[:60]}...)"
                return res

        # Default fallback to Heuristic
        return HeuristicSQLEngine.analyze_and_fix(
            query=query,
            dialect=dialect,
            error_message=error_message,
            business_requirement=business_requirement,
            schema_ddl=schema_ddl
        )
