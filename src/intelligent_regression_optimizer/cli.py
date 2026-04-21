"""CLI entry point for intelligent-regression-optimizer."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click
import yaml

from .benchmark_runner import run_assertions
from .end_to_end_flow import run_pipeline, run_pipeline_from_merged
from .excel_loader import ExcelLoaderError, load_excel
from .history_loader import load_history_csv, load_history_json
from .junit_xml_parser import parse_junit_directory
from .input_loader import InputValidationError
from .models import EXIT_INPUT_ERROR, EXIT_OK, EXIT_VALIDATION_ERROR, TestHistoryRecord


@click.group()
def main() -> None:
    """Intelligent Regression Optimizer — deterministic sprint-scoped test selection."""


@main.command()
@click.argument("input_file", type=click.Path(exists=False), required=False, default=None)
@click.option("--output", "-o", type=click.Path(), default=None, help="Write report to file instead of stdout.")
@click.option("--tests", type=click.Path(), default=None,
              help="Path to test_suite YAML file (use with --sprint).")
@click.option("--sprint", type=click.Path(), default=None,
              help="Path to sprint context YAML file (use with --tests).")
@click.option("--history-dir", type=click.Path(), default=None,
              help="Directory of JUnit XML files (one per CI run) to derive flakiness history.")
@click.option("--history-file", type=click.Path(), default=None,
              help="Pre-computed history file (.csv or .json) with flakiness metrics.")
def run(
    input_file: str | None,
    output: str | None,
    tests: str | None,
    sprint: str | None,
    history_dir: str | None,
    history_file: str | None,
) -> None:
    """Run the optimisation pipeline on INPUT_FILE and print the report.

    Alternatively, use --tests and --sprint to supply the test suite and
    sprint context as separate files. The tool merges them before running.

    Supply --history-dir (directory of JUnit XML files) or --history-file
    (pre-computed CSV/JSON) to overlay CI-derived flakiness metrics onto
    the test_suite before scoring.
    """
    # Validate argument combinations
    if input_file and (tests or sprint):
        click.echo("Error: cannot combine INPUT_FILE with --tests/--sprint flags.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if not input_file and not (tests and sprint):
        click.echo("Error: provide either INPUT_FILE or both --tests and --sprint.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if bool(tests) != bool(sprint):
        click.echo("Error: --tests and --sprint must be used together.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if history_dir and history_file:
        click.echo("Error: --history-dir and --history-file are mutually exclusive.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    # Load history when requested
    history: dict[str, TestHistoryRecord] | None = None
    if history_dir is not None:
        if not Path(history_dir).is_dir():
            click.echo(f"Error: history directory not found: {history_dir!r}", err=True)
            sys.exit(EXIT_INPUT_ERROR)
        try:
            history = parse_junit_directory(history_dir)
        except InputValidationError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(EXIT_INPUT_ERROR)

    if history_file is not None:
        hist_p = Path(history_file)
        if not hist_p.exists():
            click.echo(f"Error: history file not found: {history_file!r}", err=True)
            sys.exit(EXIT_INPUT_ERROR)
        suffix = hist_p.suffix.lower()
        if suffix == ".csv":
            try:
                history = load_history_csv(history_file)
            except InputValidationError as exc:
                click.echo(f"Error: {exc}", err=True)
                sys.exit(EXIT_INPUT_ERROR)
        elif suffix == ".json":
            try:
                history = load_history_json(history_file)
            except InputValidationError as exc:
                click.echo(f"Error: {exc}", err=True)
                sys.exit(EXIT_INPUT_ERROR)
        else:
            click.echo(
                f"Error: --history-file must be a .csv or .json file, got {hist_p.name!r}",
                err=True,
            )
            sys.exit(EXIT_INPUT_ERROR)

    if input_file:
        result = run_pipeline(input_file, history=history)
    else:
        # Merge mode — history applied inside run_pipeline_from_merged via separate helper
        result = _run_merged(tests, sprint, history=history)  # type: ignore[arg-type]

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


def _run_merged(tests_path: str, sprint_path: str, history: dict | None = None) -> Any:
    """Load two YAML files, merge them, and run the pipeline."""
    from .end_to_end_flow import merge_history
    from .models import FlowResult

    tests_p = Path(tests_path)
    sprint_p = Path(sprint_path)

    if not tests_p.exists():
        return FlowResult(
            exit_code=EXIT_INPUT_ERROR,
            message=f"Tests file not found: {tests_path!r}",
            output_path=None,
        )
    if not sprint_p.exists():
        return FlowResult(
            exit_code=EXIT_INPUT_ERROR,
            message=f"Sprint file not found: {sprint_path!r}",
            output_path=None,
        )

    with tests_p.open(encoding="utf-8") as fh:
        tests_data = yaml.safe_load(fh)
    with sprint_p.open(encoding="utf-8") as fh:
        sprint_data = yaml.safe_load(fh)

    if not isinstance(tests_data, dict):
        return FlowResult(
            exit_code=EXIT_INPUT_ERROR,
            message="Tests file must be a YAML mapping",
            output_path=None,
        )
    if not isinstance(sprint_data, dict):
        return FlowResult(
            exit_code=EXIT_INPUT_ERROR,
            message="Sprint file must be a YAML mapping",
            output_path=None,
        )

    # Extract test_suite from tests file
    if "test_suite" not in tests_data:
        return FlowResult(
            exit_code=EXIT_INPUT_ERROR,
            message="Tests file must contain a 'test_suite' key",
            output_path=None,
        )

    # Extract sprint_context and constraints from sprint file
    if "sprint_context" not in sprint_data:
        return FlowResult(
            exit_code=EXIT_INPUT_ERROR,
            message="Sprint file must contain a 'sprint_context' key",
            output_path=None,
        )
    if "constraints" not in sprint_data:
        return FlowResult(
            exit_code=EXIT_INPUT_ERROR,
            message="Sprint file must contain a 'constraints' key",
            output_path=None,
        )

    merged: dict[str, Any] = {
        "sprint_context": sprint_data["sprint_context"],
        "test_suite": tests_data["test_suite"],
        "constraints": sprint_data["constraints"],
    }

    return run_pipeline_from_merged(merged, history=history)


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

