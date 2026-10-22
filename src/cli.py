"""
Rich Terminal Command Line Interface (CLI) for AetherSDLC.
Supports executing scenarios, inspecting DAG topologies, reviewing audit logs, and interactive HITL sign-offs.
"""

from __future__ import annotations
import argparse
import asyncio
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from src.constants import (
    CLI_BANNER,
    CLI_DESCRIPTION,
    CLI_MARKER_HITL,
    CLI_MARKER_REPLAN,
    CLI_MARKER_RUNNING,
    CLI_MARKER_SUCCESS,
    SCENARIO_ALL,
    SCENARIO_AMBIGUOUS,
    SCENARIO_BROWNFIELD,
    SCENARIO_GREENFIELD,
)
from src.scenarios.ambiguous import run_ambiguous_scenario
from src.scenarios.brownfield import run_brownfield_scenario
from src.scenarios.greenfield import run_greenfield_scenario

import os
# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console()


def print_banner():
    """Display the AetherSDLC startup banner."""
    console.print(Panel(CLI_BANNER, style="bold cyan"))


def render_summary(context):
    """Render a rich terminal table summarising pipeline execution metrics."""
    table = Table(title="Execution Summary & Telemetry", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    duration = (context.end_time or 0) - context.start_time
    table.add_row("Pipeline ID", context.pipeline_id[:8] + "...")
    table.add_row("Scenario", context.scenario_name.upper())
    table.add_row("Final Status", str(context.status.value).upper())
    table.add_row("Execution Latency", f"{duration:.2f} seconds")
    table.add_row("Replanning / Self-Healing Events", str(context.replans_count))
    table.add_row("Rollbacks Executed", str(context.rollbacks_count))
    table.add_row("Audit Trail Events Logged", str(len(context.audit_events)))
    table.add_row("HITL Approvals Completed", str(len(context.approvals)))

    console.print(table)

    # Lineage Tree
    tree = Tree("[bold yellow]Decision Lineage & Governance Record[/bold yellow]")
    for rec in context.decision_lineage:
        node = tree.add(f"[bold cyan]{rec.phase.value.upper()}[/bold cyan] -> {rec.decision}")
        node.add(f"[italic]Rationale:[/italic] {rec.rationale}")
        node.add(f"[italic]Agent:[/italic] {rec.agent_name}")
    console.print(tree)


def cli_callback(event):
    """Handle pipeline SSE-like events and print them to the terminal."""
    ev_type = event.get("type")
    if ev_type == "NODE_STARTED":
        console.print(f"  [cyan]{CLI_MARKER_RUNNING} [RUNNING][/cyan] Node [bold]{event.get('node_id')}[/bold]: {event.get('node_name')}")
    elif ev_type == "NODE_COMPLETED":
        console.print(f"  [green]{CLI_MARKER_SUCCESS} [SUCCESS][/green] Node [bold]{event.get('node_id')}[/bold] finished.")
    elif ev_type == "DYNAMIC_REPLAN_TRIGGERED":
        console.print(f"  [yellow]{CLI_MARKER_REPLAN} [REPLAN][/yellow] Rescheduled minimal subgraph: {event.get('repaired_nodes')}")
    elif ev_type == "HITL_REQUESTED":
        console.print(f"  [magenta]{CLI_MARKER_HITL} [HITL GATE][/magenta] {event.get('gate_title')} [Risk: {event.get('risk_level')}]")
    elif ev_type == "HITL_RESOLVED":
        status_color = "green" if event.get("approved") else "red"
        console.print(f"  [{status_color}]{CLI_MARKER_SUCCESS} [HITL SIGNED-OFF][/{status_color}] By {event.get('reviewer')}: {event.get('comments')}")


async def main():
    """CLI entry point for AetherSDLC."""
    parser = argparse.ArgumentParser(description=CLI_DESCRIPTION)
    parser.add_argument(
        "--scenario",
        choices=[SCENARIO_GREENFIELD, SCENARIO_BROWNFIELD, SCENARIO_AMBIGUOUS, SCENARIO_ALL],
        default=SCENARIO_GREENFIELD,
        help="Scenario to run",
    )
    parser.add_argument("--manual-hitl", action="store_true", help="Prompt for manual HITL approval via terminal")
    args = parser.parse_args()

    print_banner()
    auto_approve = not args.manual_hitl

    scenarios_to_run = (
        [SCENARIO_GREENFIELD, SCENARIO_BROWNFIELD, SCENARIO_AMBIGUOUS]
        if args.scenario == SCENARIO_ALL
        else [args.scenario]
    )

    for sc in scenarios_to_run:
        console.print(f"\n[bold green]═══ LAUNCHING SCENARIO: {sc.upper()} ═══[/bold green]")
        if sc == SCENARIO_GREENFIELD:
            ctx = await run_greenfield_scenario(auto_approve=auto_approve, event_callback=cli_callback)
        elif sc == SCENARIO_BROWNFIELD:
            ctx = await run_brownfield_scenario(auto_approve=auto_approve, event_callback=cli_callback)
        elif sc == SCENARIO_AMBIGUOUS:
            ctx = await run_ambiguous_scenario(auto_approve=auto_approve, event_callback=cli_callback)

        render_summary(ctx)


if __name__ == "__main__":
    asyncio.run(main())
