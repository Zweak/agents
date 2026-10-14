"""LLM Engine for SQL Debugging & Optimization Agent.

Supports Google Gemini (via `google-genai` SDK) and OpenAI-compatible models (OpenAI, Ollama, Azure).
Provides strict JSON structured responses, chain-of-thought diagnostics, and fallback handling.
"""

import os
import json
import difflib
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from .models import AnalysisResult, DetectedIssue, IssueType, IssueSeverity, IndexRecommendation
from .analyzer import SQLStaticAnalyzer

load_dotenv()


SYSTEM_PROMPT = """You are an elite Principal Database Administrator and Senior SQL Performance Engineer.
Your task is to analyze a SQL query, identify bugs, errors, antipatterns, and performance bottlenecks,
and produce a fully corrected, highly optimized SQL query with clear educational explanations.

You must return ONLY a valid JSON object with the following schema:
{
  "root_cause": "Concise summary of why the query failed or is suboptimal",
  "issues": [
    {
      "issue_type": "Syntax Error" | "Semantic / Logic Error" | "Performance Bottleneck" | "Schema Mismatch" | "Security / Injection Risk" | "Best Practice / Anti-pattern",
      "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO",
      "summary": "Short headline of the issue",
      "detail": "Thorough technical explanation of what went wrong",
      "recommendation": "Specific remediation action"
    }
  ],
  "corrected_query": "The fully corrected, properly indented SQL query ready for production",
  "explanation": "Clear markdown explanation broken into: 1. Root Cause, 2. What Changed & Why, 3. Performance Impact",
  "changes_made": [
    "Specific change 1",
    "Specific change 2"
  ],
  "performance_notes": [
    "Performance observation 1",
    "Performance observation 2"
  ],
  "index_recommendations": [
    {
      "table_name": "table_name",
      "columns": ["col1", "col2"],
      "index_name": "idx_table_col",
      "ddl": "CREATE INDEX idx_table_col ON table_name(col1, col2);",
      "rationale": "Why this index dramatically helps this query"
    }
  ]
}

DO NOT include markdown code fences (like ```json) in your JSON output. Return pure raw JSON only.
Ensure the SQL is syntactically valid for the specified dialect.
"""


class LLMSQLEngine:
    """Invokes LLMs for advanced SQL diagnosis and optimization."""

    @classmethod
    def analyze_with_gemini(
        cls,
        query: str,
        dialect: str = "PostgreSQL",
        error_message: Optional[str] = None,
        business_requirement: Optional[str] = None,
        schema_ddl: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash"
    ) -> AnalysisResult:
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)

        user_content = cls._build_user_prompt(query, dialect, error_message, business_requirement, schema_ddl)

        response = client.models.generate_content(
            model=model_name,
            contents=[user_content],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.2,
            )
        )

        raw_json = response.text.strip()
        return cls._parse_llm_json_response(raw_json, query, dialect, error_message, business_requirement, schema_ddl, f"Gemini ({model_name})")

    @classmethod
    def analyze_with_openai(
        cls,
        query: str,
        dialect: str = "PostgreSQL",
        error_message: Optional[str] = None,
        business_requirement: Optional[str] = None,
        schema_ddl: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: str = "gpt-4o"
    ) -> AnalysisResult:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key and not base_url:
            raise ValueError("OPENAI_API_KEY is not configured.")

        from openai import OpenAI

        client = OpenAI(api_key=key or "no-key-required", base_url=base_url)

        user_content = cls._build_user_prompt(query, dialect, error_message, business_requirement, schema_ddl)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )

        raw_json = response.choices[0].message.content.strip()
        return cls._parse_llm_json_response(raw_json, query, dialect, error_message, business_requirement, schema_ddl, f"OpenAI ({model_name})")

    @classmethod
    def _build_user_prompt(
        cls,
        query: str,
        dialect: str,
        error_message: Optional[str],
        business_requirement: Optional[str],
        schema_ddl: Optional[str]
    ) -> str:
        prompt_parts = [
            f"### Target SQL Dialect\n{dialect}\n",
            f"### Original SQL Query\n```sql\n{query.strip()}\n```\n"
        ]
        if error_message:
            prompt_parts.append(f"### Database Error Message Received\n```\n{error_message.strip()}\n```\n")
        if business_requirement:
            prompt_parts.append(f"### Intended Business Requirement\n{business_requirement.strip()}\n")
        if schema_ddl:
            prompt_parts.append(f"### Database Schema DDL / Context\n```sql\n{schema_ddl.strip()}\n```\n")

        prompt_parts.append("Diagnose all issues, provide the corrected and optimized query, explain the fixes, and recommend indexes.")
        return "\n".join(prompt_parts)

    @classmethod
    def _parse_llm_json_response(
        cls,
        raw_json: str,
        original_query: str,
        dialect: str,
        error_message: Optional[str],
        business_requirement: Optional[str],
        schema_ddl: Optional[str],
        engine_name: str
    ) -> AnalysisResult:
        # Strip potential markdown fences if present
        clean_json = raw_json
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```(?:json)?\n?", "", clean_json)
            clean_json = re.sub(r"\n?```$", "", clean_json)

        data = json.loads(clean_json)

        # Merge with static AST issues
        static_issues = SQLStaticAnalyzer.analyze(original_query, schema_ddl or "")

        parsed_issues = []
        for item in data.get("issues", []):
            try:
                parsed_issues.append(
                    DetectedIssue(
                        issue_type=IssueType(item.get("issue_type", IssueType.BEST_PRACTICE.value)),
                        severity=IssueSeverity(item.get("severity", IssueSeverity.MEDIUM.value)),
                        summary=item.get("summary", "Issue detected"),
                        detail=item.get("detail", ""),
                        recommendation=item.get("recommendation", "")
                    )
                )
            except Exception:
                pass

        # Combine issues without exact duplicate summaries
        seen_summaries = {i.summary.lower() for i in parsed_issues}
        for s_issue in static_issues:
            if s_issue.summary.lower() not in seen_summaries:
                parsed_issues.append(s_issue)
                seen_summaries.add(s_issue.summary.lower())

        index_recs = []
        for idx in data.get("index_recommendations", []):
            index_recs.append(
                IndexRecommendation(
                    table_name=idx.get("table_name", "table"),
                    columns=idx.get("columns", []),
                    index_name=idx.get("index_name", "idx_recommendation"),
                    ddl=idx.get("ddl", ""),
                    rationale=idx.get("rationale", "")
                )
            )

        corrected = data.get("corrected_query", original_query).strip()

        # Compute diff
        diff_lines = list(difflib.unified_diff(
            original_query.splitlines(keepends=True),
            corrected.splitlines(keepends=True),
            fromfile="Original Query",
            tofile="Optimized Query",
            n=3
        ))
        unified_diff = "".join(diff_lines)

        return AnalysisResult(
            original_query=original_query.strip(),
            dialect=dialect,
            error_message_input=error_message,
            business_requirement_input=business_requirement,
            schema_context_input=schema_ddl,
            root_cause=data.get("root_cause", "Optimization completed."),
            issues=parsed_issues,
            corrected_query=corrected,
            diff_unified=unified_diff,
            explanation=data.get("explanation", ""),
            changes_made=data.get("changes_made", []),
            performance_notes=data.get("performance_notes", []),
            index_recommendations=index_recs,
            engine_used=engine_name
        )
