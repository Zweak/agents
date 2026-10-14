import sys
import os
import argparse
from typing import Optional

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm

from agent.core import SQLAgent
from agent.presets import PRESET_SCENARIOS
from agent.models import AnalysisResult

console = Console(force_terminal=True)


def print_banner():
    banner_text = (
        "[bold cyan]🔍 SQL Debugging & Optimization Agent[/bold cyan]\n"
        "[dim]Automated AST Anti-Pattern Linting • Plan Verification • Index Engineering • Dialect Rewrites[/dim]"
    )
    console.print(Panel(banner_text, border_style="cyan"))


def display_result(result: AnalysisResult):
    console.print()
    # 1. Summary Header
    summary_table = Table(title="[bold yellow]Analysis Summary[/bold yellow]", border_style="yellow")
    summary_table.add_column("Property", style="bold cyan")
    summary_table.add_column("Value")
    summary_table.add_row("Engine Used", result.engine_used)
    summary_table.add_row("Target Dialect", result.dialect)
    summary_table.add_row("Execution Verified", "✅ YES (Sandbox Test Passed)" if result.execution_verified else "⚠️ Not Verified")
    summary_table.add_row("Analysis Time", f"{result.time_taken_seconds:.3f} seconds")
    console.print(summary_table)

    # 2. Root Cause
    console.print(Panel(
        f"[bold red]Root Cause:[/bold red] {result.root_cause}",
        title="[bold red]🚨 Diagnosis[/bold red]",
        border_style="red"
    ))

    # 3. Detected Issues
    if result.issues:
        issues_table = Table(title="[bold magenta]Detected Anti-Patterns & Issues[/bold magenta]", border_style="magenta")
        issues_table.add_column("Type", style="cyan")
        issues_table.add_column("Severity", style="bold")
        issues_table.add_column("Summary")
        issues_table.add_column("Recommendation", style="green")

        for iss in result.issues:
            sev_color = "red" if iss.severity in ("CRITICAL", "HIGH") else "yellow"
            issues_table.add_row(
                iss.issue_type.value if hasattr(iss.issue_type, 'value') else str(iss.issue_type),
                f"[{sev_color}]{iss.severity.value if hasattr(iss.severity, 'value') else str(iss.severity)}[/{sev_color}]",
                iss.summary,
                iss.recommendation
            )
        console.print(issues_table)

    # 4. Corrected Query
    console.print()
    console.print("[bold green]✨ Corrected & Optimized SQL Query:[/bold green]")
    syntax_corrected = Syntax(result.corrected_query, "sql", theme="monokai", line_numbers=True)
    console.print(syntax_corrected)

    # 5. Diff if available
    if result.diff_unified:
        console.print()
        console.print("[bold cyan]Diff (Unified):[/bold cyan]")
        syntax_diff = Syntax(result.diff_unified, "diff", theme="monokai", line_numbers=False)
        console.print(syntax_diff)

    # 6. Changes & Explanations
    if result.changes_made:
        console.print()
        console.print(Panel(
            "\n".join(f"• [bold green]{c}[/bold green]" for c in result.changes_made),
            title="[bold green]🛠️ Actions Taken[/bold green]",
            border_style="green"
        ))

    # 7. Sandbox Execution Verification
    if result.corrected_execution and result.corrected_execution.success:
        exec_info = (
            f"Execution time: [bold cyan]{result.corrected_execution.execution_time_ms} ms[/bold cyan]\n"
            f"Returned rows: [bold cyan]{result.corrected_execution.row_count}[/bold cyan]\n"
        )
        if result.corrected_execution.sample_rows:
            exec_info += f"Sample row: [dim]{result.corrected_execution.sample_rows[0]}[/dim]"
        console.print(Panel(exec_info, title="[bold blue]🧪 Live Database Sandbox Result[/bold blue]", border_style="blue"))

    # 8. Index Recommendations
    if result.index_recommendations:
        console.print()
        idx_table = Table(title="[bold blue]⚡ Recommended Database Indexes[/bold blue]", border_style="blue")
        idx_table.add_column("Table", style="cyan")
        idx_table.add_column("Index DDL", style="green")
        idx_table.add_column("Rationale")

        for idx in result.index_recommendations:
            idx_table.add_row(idx.table_name, idx.ddl, idx.rationale)
        console.print(idx_table)


def run_interactive_demo(agent: SQLAgent):
    console.print("\n[bold yellow]=== Interactive Presentation Walkthrough ===[/bold yellow]\n")
    for i, scenario in enumerate(PRESET_SCENARIOS, 1):
        console.print(Panel(
            f"[bold]{scenario['title']}[/bold]\n[dim]{scenario['subtitle']}[/dim]\n\n"
            f"[bold cyan]Query:[/bold cyan]\n{scenario['query']}\n\n"
            f"[bold yellow]Highlight:[/bold yellow] {scenario['highlight']}",
            title=f"Scenario {i} of {len(PRESET_SCENARIOS)}",
            border_style="cyan"
        ))
        if not Confirm.ask(f"Run Agent on Scenario {i}?", default=True):
            continue

        with console.status(f"[cyan]Analyzing Scenario {i}...[/cyan]"):
            result = agent.diagnose_and_optimize(
                query=scenario["query"],
                dialect=scenario["dialect"],
                error_message=scenario["error_message"],
                business_requirement=scenario["business_requirement"],
                schema_ddl=scenario["schema_ddl"],
                seed_data=scenario["seed_data"]
            )

        display_result(result)
        console.print("\n" + "="*80 + "\n")
        if i < len(PRESET_SCENARIOS):
            if not Confirm.ask("Proceed to next scenario?", default=True):
                break


def main():
    parser = argparse.ArgumentParser(description="SQL Debugging & Optimization Agent CLI")
    parser.add_argument("--demo", action="store_true", help="Run interactive presentation demo of all 5 scenarios")
    parser.add_argument("--scenario", type=int, choices=range(1, 6), help="Run a specific preset scenario (1-5)")
    parser.add_argument("--query", type=str, help="SQL query to debug or optimize")
    parser.add_argument("--error", type=str, help="Error message received from database")
    parser.add_argument("--requirement", type=str, help="Business requirement / expected output")
    parser.add_argument("--dialect", type=str, default="PostgreSQL", help="SQL dialect (PostgreSQL, MySQL, SQLite, etc.)")
    parser.add_argument("--provider", type=str, default="auto", choices=["auto", "gemini", "openai", "heuristic"], help="LLM Provider or offline heuristic")

    args = parser.parse_args()
    print_banner()

    agent = SQLAgent(provider=args.provider)

    if args.demo:
        run_interactive_demo(agent)
        return

    if args.scenario:
        sc = PRESET_SCENARIOS[args.scenario - 1]
        console.print(f"[bold cyan]Running Preset Scenario {args.scenario}: {sc['title']}[/bold cyan]")
        result = agent.diagnose_and_optimize(
            query=sc["query"],
            dialect=sc["dialect"],
            error_message=sc["error_message"],
            business_requirement=sc["business_requirement"],
            schema_ddl=sc["schema_ddl"],
            seed_data=sc["seed_data"]
        )
        display_result(result)
        return

    if args.query:
        result = agent.diagnose_and_optimize(
            query=args.query,
            dialect=args.dialect,
            error_message=args.error,
            business_requirement=args.requirement
        )
        display_result(result)
        return

    # No arguments provided: Interactive prompt
    console.print("\n[bold]Select an action:[/bold]")
    console.print("1. Run Full Presentation Demo (5 Scenarios)")
    console.print("2. Select a Preset Scenario (1 to 5)")
    console.print("3. Enter a Custom SQL Query to Debug")
    console.print("4. Exit")

    choice = Prompt.ask("Enter choice", choices=["1", "2", "3", "4"], default="1")
    if choice == "1":
        run_interactive_demo(agent)
    elif choice == "2":
        sc_num = Prompt.ask("Choose scenario number", choices=["1", "2", "3", "4", "5"], default="1")
        sc = PRESET_SCENARIOS[int(sc_num) - 1]
        result = agent.diagnose_and_optimize(
            query=sc["query"],
            dialect=sc["dialect"],
            error_message=sc["error_message"],
            business_requirement=sc["business_requirement"],
            schema_ddl=sc["schema_ddl"],
            seed_data=sc["seed_data"]
        )
        display_result(result)
    elif choice == "3":
        user_query = Prompt.ask("Paste SQL Query")
        user_err = Prompt.ask("Paste Error Message (optional)", default="")
        user_req = Prompt.ask("Paste Business Requirement (optional)", default="")
        user_dial = Prompt.ask("Dialect", default="PostgreSQL")
        result = agent.diagnose_and_optimize(
            query=user_query,
            dialect=user_dial,
            error_message=user_err or None,
            business_requirement=user_req or None
        )
        display_result(result)


if __name__ == "__main__":
    main()
