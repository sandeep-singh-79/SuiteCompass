"""CLI entry point for intelligent-regression-optimizer."""

from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml

from .benchmark_runner import run_assertions
from .end_to_end_flow import run_pipeline
from .excel_loader import ExcelLoaderError, load_excel
from .models import EXIT_INPUT_ERROR, EXIT_OK, EXIT_VALIDATION_ERROR


@click.group()
def main() -> None:
    """Intelligent Regression Optimizer — deterministic sprint-scoped test selection."""


@main.command()
@click.argument("input_file", type=click.Path(exists=False))
@click.option("--output", "-o", type=click.Path(), default=None, help="Write report to file instead of stdout.")
def run(input_file: str, output: str | None) -> None:
    """Run the optimisation pipeline on INPUT_FILE and print the report."""
    result = run_pipeline(input_file)

    if result.exit_code == EXIT_INPUT_ERROR:
        click.echo(f"Error: {result.message}", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if result.exit_code == EXIT_VALIDATION_ERROR:
        click.echo(f"Validation error: {result.message}", err=True)
        sys.exit(EXIT_VALIDATION_ERROR)

    if output:
        Path(output).write_text(result.message, encoding="utf-8")
    else:
        click.echo(result.message)

    sys.exit(EXIT_OK)


@main.command()
@click.argument("input_file", type=click.Path(exists=False))
@click.argument("assertions_file", type=click.Path(exists=False))
def benchmark(input_file: str, assertions_file: str) -> None:
    """Run INPUT_FILE through the pipeline and validate against ASSERTIONS_FILE."""
    # Run the pipeline first — propagates input errors as exit 2
    result = run_pipeline(input_file)

    if result.exit_code == EXIT_INPUT_ERROR:
        click.echo(f"Error: {result.message}", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if result.exit_code == EXIT_VALIDATION_ERROR:
        click.echo(f"Validation error: {result.message}", err=True)
        sys.exit(EXIT_VALIDATION_ERROR)

    # Check assertions file exists before running
    if not Path(assertions_file).exists():
        click.echo(f"Error: assertions file not found: {assertions_file}", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    ar = run_assertions(result.message, assertions_file)

    if ar.is_valid:
        click.echo(f"OK — {ar.total_checks} checks passed.")
        sys.exit(EXIT_OK)
    else:
        click.echo("FAIL — assertion errors:", err=True)
        for err in ar.errors:
            click.echo(f"  - {err}", err=True)
        sys.exit(1)


@main.command("import-tests")
@click.argument("xlsx_file", type=click.Path(exists=False))
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Write generated YAML to file instead of stdout.")
@click.option("--sheet", "-s", type=str, default=None,
              help="Sheet name to read (default: 'Tests' sheet, else first sheet).")
def import_tests(xlsx_file: str, output: str | None, sheet: str | None) -> None:
    """Import a test inventory from XLSX_FILE and emit a test_suite YAML block.

    The output contains only the test_suite section. Merge it with a
    sprint_context + constraints YAML, then run: iro run <combined.yaml>
    """
    try:
        tests = load_excel(xlsx_file, sheet=sheet)
    except ExcelLoaderError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    # Render test_suite section only
    test_suite_yaml = yaml.dump(
        {"test_suite": tests},
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    if output:
        Path(output).write_text(test_suite_yaml, encoding="utf-8")
        click.echo(f"Written to {output}")
    else:
        click.echo(test_suite_yaml)

    sys.exit(EXIT_OK)

