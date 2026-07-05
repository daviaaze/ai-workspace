"""CLI commands — `aiw eval`."""

from __future__ import annotations

import typer
from rich.table import Table

from ai_workspace.cli._app import app, console

# ── Eval commands ─────────────────────────────────────────

eval_app = typer.Typer(help="Agent evaluation harness")
app.add_typer(eval_app, name="eval")


@eval_app.command(name="run")
def eval_run(
    suite: str = typer.Option("all", "--suite", "-s", help="Suite: all, coding, reasoning, facts"),
    model: str = typer.Option("qwen3:14b", "--model", "-m", help="Model to evaluate"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="Provider"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate eval definitions without LLM calls"),
):
    """Run agent evaluation suites."""
    from ai_workspace.evals import ALL_EVAL_SUITES, EvalRunner

    console.print("[bold cyan]Eval Harness[/]")
    console.print(f"[dim]Model: {model} | Provider: {provider} | Suite: {suite}[/]")
    console.print()

    suite_names = list(ALL_EVAL_SUITES.keys()) if suite == "all" else [suite]

    if dry_run:
        runner = EvalRunner(model=model, provider=provider)
        all_cases = []
        for name in suite_names:
            all_cases.extend(ALL_EVAL_SUITES.get(name, []))
        import asyncio as _asyncio
        results = _asyncio.run(runner.run_dry(all_cases))
        console.print(f"[dim]Dry run: {len(results)} case definitions validated.[/]")
        return

    from ai_workspace.evals import run_all_evals

    suite_results = _asyncio.run(run_all_evals(
        model=model, provider=provider, suites=suite_names,
    ))

    table = Table(title=" Eval Results")
    table.add_column("Suite", style="cyan")
    table.add_column("Passed", justify="right")
    table.add_column("Rate", justify="right")
    table.add_column("Avg Latency", justify="right")
    table.add_column("Avg Tokens", justify="right")

    total_passed = 0
    total_cases = 0

    for name, sr in suite_results.items():
        icon = "" if sr.pass_rate >= 0.8 else ("" if sr.pass_rate >= 0.5 else "")
        table.add_row(
            f"{icon} {name}",
            f"{sr.passed_count}/{sr.total_cases}",
            f"{sr.pass_rate:.0%}",
            f"{sr.avg_latency_ms:.0f}ms",
            f"{sr.avg_tokens:.0f}",
        )
        total_passed += sr.passed_count
        total_cases += sr.total_cases

    console.print(table)
    console.print()
    overall = total_passed / total_cases if total_cases > 0 else 0
    console.print(f"[bold]Overall: {total_passed}/{total_cases} passed ({overall:.0%})[/]")


@eval_app.command(name="list")
def eval_list():
    """List available eval suites and their cases."""
    from ai_workspace.evals import ALL_EVAL_SUITES

    for name, cases in ALL_EVAL_SUITES.items():
        console.print(f"[bold cyan]{name}[/] ({len(cases)} cases)")
        for case in cases:
            expected = []
            if case.expected_keywords:
                expected.append(f"keys: {', '.join(case.expected_keywords[:3])}")
            if case.forbidden_keywords:
                expected.append(f"forbidden: {', '.join(case.forbidden_keywords[:2])}")
            if case.expected_tools:
                expected.append(f"tools: {', '.join(case.expected_tools)}")
            extra = f" [{'; '.join(expected)}]" if expected else ""
            console.print(f"  [dim]{case.id}[/]: {case.task[:80]}...{extra}")
        console.print()


if __name__ == "__main__":
    app()
