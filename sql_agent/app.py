"""Streamlit Web Application for SQL Debugging & Optimization Agent.

Provides an interactive presentation-ready UI with 1-click preset scenarios,
side-by-side SQL diffing, live in-memory sandbox execution, and index engineering.
"""

import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from agent.core import SQLAgent
from agent.presets import PRESET_SCENARIOS
from agent.models import SQLDialect, IssueSeverity

load_dotenv()

st.set_page_config(
    page_title="SQL Debugging & Optimization Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .badge-critical { background-color: #EF4444; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .badge-high { background-color: #F97316; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .badge-medium { background-color: #FBBF24; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .badge-low { background-color: #3B82F6; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .stCodeBlock { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/database.png", width=64)
    st.title("Agent Controls")
    
    mode = st.radio(
        "Operating Mode:",
        ["🚀 Preset Scenarios (Presentation Demo)", "✏️ Custom Query Debugger"],
        index=0
    )
    
    st.markdown("---")
    st.subheader("⚙️ Engine Configuration")
    
    provider_choice = st.selectbox(
        "AI Provider / Engine:",
        ["Built-in Expert Engine (Offline / Deterministic)", "Google Gemini", "OpenAI (GPT-4o)"],
        index=0
    )
    
    provider_map = {
        "Built-in Expert Engine (Offline / Deterministic)": "heuristic",
        "Google Gemini": "gemini",
        "OpenAI (GPT-4o)": "openai"
    }
    provider = provider_map[provider_choice]
    
    api_key_input = ""
    model_name = ""
    if provider == "gemini":
        default_gemini = os.getenv("GEMINI_API_KEY", "")
        api_key_input = st.text_input("Gemini API Key:", value=default_gemini, type="password")
        model_name = st.text_input("Gemini Model:", value="gemini-2.5-flash")
    elif provider == "openai":
        default_openai = os.getenv("OPENAI_API_KEY", "")
        api_key_input = st.text_input("OpenAI API Key:", value=default_openai, type="password")
        model_name = st.text_input("OpenAI Model:", value="gpt-4o")
        
    dialect = st.selectbox(
        "Target SQL Dialect:",
        [d.value for d in SQLDialect],
        index=0
    )
    
    verify_sandbox = st.checkbox("🧪 Test in In-Memory SQLite Sandbox", value=True)
    
    st.markdown("---")
    st.markdown("💡 **Tip for Presentation:** The *Built-in Expert Engine* requires zero API keys and works 100% offline with instant sub-millisecond execution.")


# --- MAIN HEADER ---
st.markdown('<div class="main-header">🔍 SQL Debugging & Optimization Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Automated syntax debugging, anti-pattern linting, query rewrite, and execution plan optimization.</div>', unsafe_allow_html=True)


# --- INPUT SETUP ---
query_input = ""
error_input = ""
req_input = ""
schema_input = ""
seed_input = ""

if mode.startswith("🚀"):
    st.markdown("### 📋 Select a Presentation Demo Scenario")
    scenario_titles = [f"{s['title']} — {s['subtitle']}" for s in PRESET_SCENARIOS]
    selected_idx = st.selectbox("Choose Scenario to Demonstrate:", range(len(PRESET_SCENARIOS)), format_func=lambda i: scenario_titles[i])
    
    sc = PRESET_SCENARIOS[selected_idx]
    
    st.info(f"**Scenario Context:** {sc['highlight']}\n\n**Business Requirement:** {sc['business_requirement']}")
    
    col1, col2 = st.columns(2)
    with col1:
        query_input = st.text_area("Original SQL Query (Problematic):", value=sc["query"], height=220)
        error_input = st.text_input("Database Error Message (if any):", value=sc.get("error_message", ""))
    with col2:
        req_input = st.text_area("Business Intent / Requirement:", value=sc.get("business_requirement", ""), height=100)
        with st.expander("View Database Schema (DDL) & Test Data", expanded=False):
            schema_input = st.text_area("Schema DDL:", value=sc.get("schema_ddl", ""), height=120)
            seed_input = sc.get("seed_data", "")
            st.code(schema_input, language="sql")

else:
    st.markdown("### ✍️ Enter Custom SQL Query to Analyze")
    col1, col2 = st.columns(2)
    with col1:
        query_input = st.text_area("SQL Query to Debug:", height=200, placeholder="SELECT * FROM orders WHERE ...")
        error_input = st.text_input("Database Error Message (optional):", placeholder="e.g. column must appear in the GROUP BY clause...")
    with col2:
        req_input = st.text_area("Business Intent / Requirement (optional):", height=100, placeholder="e.g. Calculate monthly revenue per customer...")
        with st.expander("Database Schema DDL (optional for sandbox execution)", expanded=False):
            schema_input = st.text_area("Schema DDL:", height=120, placeholder="CREATE TABLE orders (...);")


# --- RUN AGENT BUTTON ---
if st.button("⚡ Run Diagnostic & Optimization Agent", type="primary", use_container_width=True):
    if not query_input.strip():
        st.warning("Please provide a SQL query to analyze.")
    else:
        with st.spinner("🤖 Agent analyzing query AST, anti-patterns, and verifying execution..."):
            agent = SQLAgent(
                provider=provider,
                api_key=api_key_input or None,
                model_name=model_name or None
            )
            result = agent.diagnose_and_optimize(
                query=query_input,
                dialect=dialect,
                error_message=error_input or None,
                business_requirement=req_input or None,
                schema_ddl=schema_input or None,
                seed_data=seed_input or None,
                verify_in_sandbox=verify_sandbox
            )
            st.session_state["result"] = result


# --- RESULTS DISPLAY ---
if "result" in st.session_state:
    res = st.session_state["result"]
    
    st.markdown("---")
    
    # Metrics Bar
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Engine Used", res.engine_used.split("(")[0].strip())
    m2.metric("Analysis Latency", f"{res.time_taken_seconds:.3f} s")
    m3.metric("Issues Detected", len(res.issues))
    m4.metric("Sandbox Verification", "✅ Passed" if res.execution_verified else "⚠️ N/A or Unverified")
    
    # Root Cause Alert
    st.error(f"**Root Cause Diagnosis:** {res.root_cause}")
    
    # Tabs
    tab_fix, tab_perf, tab_sandbox, tab_edu, tab_export = st.tabs([
        "🔍 Diagnosis & Corrected SQL",
        "⚡ Performance & Indexes",
        "🧪 Live Database Sandbox",
        "🎓 Why This Failed & Best Practices",
        "📄 Export Report"
    ])
    
    # TAB 1: Diagnosis & Fix
    with tab_fix:
        col_orig, col_fixed = st.columns(2)
        with col_orig:
            st.subheader("❌ Original Query")
            st.code(res.original_query, language="sql")
        with col_fixed:
            st.subheader("✅ Corrected & Optimized Query")
            st.code(res.corrected_query, language="sql")
            
        st.markdown("#### 🛠️ Key Improvements Made")
        for change in res.changes_made:
            st.markdown(f"- ✅ **{change}**")
            
        if res.diff_unified:
            with st.expander("View Unified Diff (Line-by-line changes)", expanded=False):
                st.code(res.diff_unified, language="diff")

    # TAB 2: Performance & Indexes
    with tab_perf:
        st.subheader("Detected Anti-Patterns & Inefficiencies")
        if res.issues:
            for iss in res.issues:
                sev_color = {
                    "CRITICAL": "badge-critical",
                    "HIGH": "badge-high",
                    "MEDIUM": "badge-medium",
                    "LOW": "badge-low"
                }.get(str(iss.severity), "badge-low")
                
                with st.container():
                    st.markdown(f"**{iss.summary}** <span class='{sev_color}'>{iss.severity}</span>", unsafe_allow_html=True)
                    st.write(iss.detail)
                    st.info(f"👉 **Recommendation:** {iss.recommendation}")
                    st.markdown("<hr style='margin: 8px 0'>", unsafe_allow_html=True)
        else:
            st.success("No static anti-patterns detected.")
            
        st.subheader("⚡ Recommended Database Indexes")
        if res.index_recommendations:
            for idx in res.index_recommendations:
                st.markdown(f"**Table:** `{idx.table_name}` | **Index:** `{idx.index_name}`")
                st.code(idx.ddl, language="sql")
                st.caption(f"**Rationale:** {idx.rationale}")
        else:
            st.write("No additional indexes strictly required.")
            
        if res.performance_notes:
            st.markdown("#### 📈 Performance & Scalability Insights")
            for note in res.performance_notes:
                st.markdown(f"- 💡 {note}")

    # TAB 3: Sandbox Execution
    with tab_sandbox:
        st.subheader("🧪 In-Memory Sandbox Query Execution")
        st.write("The agent test-executes queries against an embedded SQLite database engine to verify syntax and inspect the Query Planner.")
        
        sb_col1, sb_col2 = st.columns(2)
        with sb_col1:
            st.markdown("**Original Query Execution:**")
            if res.original_execution:
                if res.original_execution.success:
                    st.success(f"Execution succeeded ({res.original_execution.execution_time_ms} ms, {res.original_execution.row_count} rows)")
                else:
                    st.error(f"❌ Failed: {res.original_execution.error_message}")
                if res.original_execution.plan:
                    st.markdown("**Original Query Plan:**")
                    st.code(res.original_execution.plan.raw_plan)
            else:
                st.info("Original query was not executed in sandbox.")
                
        with sb_col2:
            st.markdown("**Corrected Query Execution:**")
            if res.corrected_execution:
                if res.corrected_execution.success:
                    st.success(f"✅ Succeeded ({res.corrected_execution.execution_time_ms} ms, {res.corrected_execution.row_count} rows)")
                    if res.corrected_execution.sample_rows:
                        st.markdown("**Resulting Data Preview:**")
                        df = pd.DataFrame(res.corrected_execution.sample_rows)
                        st.dataframe(df, use_container_width=True)
                else:
                    st.error(f"❌ Failed: {res.corrected_execution.error_message}")
                if res.corrected_execution.plan:
                    st.markdown("**Optimized Query Plan:**")
                    st.code(res.corrected_execution.plan.raw_plan)
                    if res.corrected_execution.plan.cost_notes:
                        st.caption(f"Plan Notes: {res.corrected_execution.plan.cost_notes}")
            else:
                st.info("Sandbox verification not available.")

    # TAB 4: Educational Explanation
    with tab_edu:
        st.subheader("🎓 Technical Deep Dive & Educational Breakdown")
        st.markdown(res.explanation)
        
        st.markdown("---")
        st.markdown("### 📚 SQL Engineering Quick Reference")
        with st.expander("1. SARGable Queries vs Non-SARGable Functions"):
            st.markdown("""
            **What is SARGable?** SARGable stands for *Search Argument Able*.
            - **Bad (Non-SARGable):** `WHERE YEAR(created_at) = 2025`
              The database cannot use the index on `created_at` because the function `YEAR()` must be evaluated for every row.
            - **Good (SARGable):** `WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01'`
              The engine jumps directly to the start position in the B-Tree index and performs an index range scan.
            """)
        with st.expander("2. The Dangerous NOT IN (SELECT ...) Trap"):
            st.markdown("""
            In SQL, `NULL` represents an *unknown* value.
            When evaluating `x NOT IN (1, 2, NULL)`:
            - If `x = 3`, `(3 != 1) AND (3 != 2) AND (3 != NULL)`.
            - `3 != NULL` evaluates to `UNKNOWN`.
            - `TRUE AND TRUE AND UNKNOWN` yields `UNKNOWN` (falsy in WHERE clause).
            - Therefore, if a subquery contains even **one NULL**, `NOT IN` returns **0 rows**.
            - **Always use `NOT EXISTS` instead.**
            """)

    # TAB 5: Export
    with tab_export:
        st.subheader("📄 Export Diagnostic Report")
        markdown_report = f"""# SQL Debugging & Optimization Report
Generated by SQL Debugging & Optimization Agent

## 1. Summary
- **Target Dialect:** {res.dialect}
- **Engine Used:** {res.engine_used}
- **Latency:** {res.time_taken_seconds:.3f} s
- **Sandbox Verified:** {'Yes' if res.execution_verified else 'No'}

## 2. Root Cause
{res.root_cause}

## 3. Original Query
```sql
{res.original_query}
```

## 4. Corrected & Optimized Query
```sql
{res.corrected_query}
```

## 5. Changes Made
{chr(10).join(f"- {c}" for c in res.changes_made)}

## 6. Index Recommendations
{chr(10).join(f"```sql{chr(10)}{i.ddl}{chr(10)}```" for i in res.index_recommendations)}
"""
        st.download_button(
            label="📥 Download Markdown Report",
            data=markdown_report,
            file_name="sql_optimization_report.md",
            mime="text/markdown"
        )
        st.text_area("Report Preview", value=markdown_report, height=300)
