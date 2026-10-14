# 🔍 SQL Debugging & Optimization Agent

An intelligent, multi-stage AI Agent designed to solve SQL syntax errors, semantic logic bugs, and database performance bottlenecks. It combines **deterministic AST static linting**, **in-memory database sandbox execution & plan verification**, and **AI reasoning** to deliver production-ready, verified SQL rewrites.

---

## 🌟 Why This Exists (The Problem)

In day-to-day engineering, writing and maintaining SQL queries comes with recurring friction:
1. **Cryptic Database Syntax Errors:** Databases often emit unhelpful errors (e.g. `column must appear in the GROUP BY clause or be used in an aggregate function`, `syntax error near "FROM"`).
2. **Silent Semantic & Logic Bugs:** Queries that execute without syntax errors but produce completely wrong numbers (e.g., accidental Cartesian products duplicating financial totals, `NOT IN (SELECT ...)` returning zero rows due to NULL values, unintentional outer-join nullification).
3. **Silent Performance Killers:** Non-SARGable WHERE predicates (e.g., `WHERE DATE(order_date) = '2025-01-01'`), missing covering indexes, unindexed foreign keys, and O(N²) correlated subqueries that bring production databases to a crawl.

This agent acts as an automated Senior Database Administrator & SQL Performance Engineer.

---

## 🏗️ Architecture: Why It's an "Agent", Not Just a Prompt

A simple prompt wrapper only sends text to an LLM and hopes for the best. This system is a true **Autonomous Agentic Workflow**:

```mermaid
flowchart TD
    A[Input: Query + Error + Requirement + Schema] --> B[Static AST & Anti-Pattern Linter]
    B --> C{Execution Mode}
    C -->|API Key Available| D[LLM Reasoning Engine: Gemini / OpenAI]
    C -->|Offline / Zero Key| E[Built-in Deterministic Expert Engine]
    D --> F[Sandboxed Database Execution & EXPLAIN Plan]
    E --> F
    F --> G{Execution Passed?}
    G -->|Yes| H[Generate Visual Diff + Metrics + Index DDL]
    G -->|No (Refinement)| I[Reflect, Fix Dialect Syntax & Re-verify]
    I --> F
    H --> J[Final Verified Output: Web UI & CLI]
```

### Key Agent Capabilities:
1. **Perception & Context Ingestion:** Analyzes SQL dialect (PostgreSQL, MySQL, SQLite, Snowflake, BigQuery, T-SQL), error messages, business requirements, and database schema DDL.
2. **Static AST Analysis (`agent/analyzer.py`):** Lints for `SELECT *`, non-SARGable function calls on indexed columns, Cartesian comma-joins, `NOT IN` subquery traps, pagination without ordering, and misaligned `HAVING` filters.
3. **Live Database Sandbox (`agent/sandbox.py`):** Test-executes queries against an embedded SQLite database, executes `EXPLAIN QUERY PLAN`, and compares execution results before and after the fix.
4. **Dual Engine Support:**
   - **Built-in Expert Engine:** 100% offline, zero API keys required, deterministic, runs in < 5ms.
   - **LLM Engine:** Integrates Google Gemini (`gemini-2.5-flash`) and OpenAI (`gpt-4o`).
5. **Side-by-Side Diff & Index Engineering:** Generates unified diffs and production-ready `CREATE INDEX` statements with technical rationales.

## 🚀 Quick Start (Bash)

### 1. Environment Setup (venv)
Set up an isolated virtual environment and install the required dependencies:

```bash
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate the virtual environment
# On Linux/macOS or Git Bash (Windows):
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Launch the Streamlit Web Application
```bash
./start_web.sh
```
Or directly:
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

### 3. Run the Terminal CLI Demo
```bash
./run_demo.sh
```
Or run a specific scenario:
```bash
python cli.py --scenario 1
python cli.py --scenario 4
```

### 4. Run the Automated Test Suite
```bash
./test_agent.sh
```

---

## 🎯 5 Core Demonstration Scenarios

| # | Scenario | Problem Category | Real-world Impact |
|---|---|---|---|
| **1** | **Cryptic GROUP BY Error** | Syntax / Semantic | Analyst selects scalar columns (`first_name`) with aggregates without grouping. |
| **2** | **Silent Cartesian Join** | Logic / Data Integrity | Missing join condition between customers and orders blows up row count and memory. |
| **3** | **Non-SARGable WHERE Clause** | Performance / Indexing | `strftime('%Y', order_date)` ignores indexes and forces full table scans. |
| **4** | **Dangerous NOT IN Null Trap** | SQL Three-Valued Logic | If subquery contains a single NULL (guest checkout), query returns 0 rows. |
| **5** | **Correlated Subquery -> CTE** | Architectural Modernization | O(N²) quadratic nested loop replaced with single-pass `ROW_NUMBER()` window function. |

---

## 📁 Project Structure

```
sql_agent2/
├── agent/
│   ├── __init__.py          # Public agent exports
│   ├── core.py              # Main SQLAgent orchestrator
│   ├── analyzer.py          # Static AST / anti-pattern & SARGability linter
│   ├── sandbox.py           # In-memory SQLite execution & EXPLAIN QUERY PLAN engine
│   ├── heuristic_engine.py  # 100% offline deterministic expert engine
│   ├── llm_engine.py        # Gemini & OpenAI API integration
│   ├── models.py            # Pydantic data schemas
│   └── presets.py           # Preloaded realistic presentation scenarios
├── tests/
│   └── test_scenarios.py    # Automated test suite
├── app.py                   # Streamlit interactive Web Application
├── cli.py                   # Rich-formatted interactive terminal CLI
├── start_web.sh             # Bash launcher for Web UI
├── run_demo.sh              # Bash launcher for interactive demo
├── cli.sh                   # Bash wrapper for CLI
├── test_agent.sh            # Bash runner for test suite
├── PRESENTATION_GUIDE.md    # 15-minute presentation script & speaker notes
├── .env.example             # Example API key configuration
└── requirements.txt         # Dependencies
```

---

## ⚙️ Environment Variables (Optional)

Create a `.env` file if you wish to use live LLMs:
```env
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```
*Note: If no API keys are provided, the agent automatically defaults to the Built-in Expert Engine so presentations never fail.*
