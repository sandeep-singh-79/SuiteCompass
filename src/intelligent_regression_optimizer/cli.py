"""CLI entry point for intelligent-regression-optimizer."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import click
import yaml

from .benchmark_runner import run_assertions
from .diff_mapper import apply_area_map, load_area_map, map_files_to_areas, parse_diff_output
from .end_to_end_flow import run_pipeline, run_pipeline_from_merged
from .excel_loader import ExcelLoaderError, load_excel
from .history_loader import load_history_csv, load_history_json
from .junit_xml_parser import parse_junit_directory
from .input_loader import InputValidationError
from .models import EXIT_INPUT_ERROR, EXIT_OK, EXIT_VALIDATION_ERROR, TestHistoryRecord
from .llm_flow import run_llm_pipeline
from .config_loader import load_llm_config
from .client_factory import create_llm_client


@click.group()
def main() -> None:
    """Intelligent Regression Optimizer — deterministic sprint-scoped test selection."""


@main.command()
@click.argument("input_file", type=click.Path(exists=False), required=False, default=None)
@click.option("--output", "-o", type=click.Path(), default=None, help="Write report to file instead of stdout.")
@click.option("--mode", type=click.Choice(["deterministic", "llm", "compare"]), default="deterministic",
              help="Recommendation mode: deterministic (default), llm, or compare.")
@click.option("--provider", type=str, default=None, help="LLM provider (openai, ollama, gemini).")
@click.option("--model", type=str, default=None, help="LLM model identifier.")
@click.option("--base-url", type=str, default=None, help="LLM provider base URL override.")
@click.option("--temperature", type=float, default=None, help="LLM sampling temperature.")
@click.option("--max-tokens", type=int, default=None, help="LLM max response tokens.")
@click.option("--config", "llm_config", type=click.Path(), default=None, help="Path to LLM config YAML.")
@click.option("--tests", type=click.Path(), default=None,
              help="Path to test_suite YAML file (use with --sprint).")
@click.option("--sprint", type=click.Path(), default=None,
              help="Path to sprint context YAML file (use with --tests).")
@click.option("--history-dir", type=click.Path(), default=None,
              help="Directory of JUnit XML files (one per CI run) to derive flakiness history.")
@click.option("--history-file", type=click.Path(), default=None,
              help="Pre-computed history file (.csv or .json) with flakiness metrics.")
@click.option("--area-map", type=click.Path(), default=None,
              help="area-map.yaml config for deriving changed_areas from git diff.")
@click.option("--diff-file", type=click.Path(), default=None,
              help="File containing 'git diff --name-only' output (use with --area-map).")
@click.option("--ref", type=str, default=None,
              help="Git ref to diff against (default HEAD~1, use with --area-map).")
@click.option("--summary-only", is_flag=True, default=False,
              help="Output only the Optimisation Summary section of the report.")
def run(
    input_file: str | None,
    output: str | None,
    mode: str,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    temperature: float | None,
    max_tokens: int | None,
    llm_config: str | None,
    tests: str | None,
    sprint: str | None,
    history_dir: str | None,
    history_file: str | None,
    area_map: str | None,
    diff_file: str | None,
    ref: str | None,
    summary_only: bool,
) -> None:
    """Run the optimisation pipeline on INPUT_FILE and print the report.

    Alternatively, use --tests and --sprint to supply the test suite and
    sprint context as separate files. The tool merges them before running.

    Supply --history-dir or --history-file to overlay CI-derived flakiness
    metrics onto the test_suite before scoring.

    Supply --area-map with --diff-file or --ref to auto-derive changed_areas
    for all stories from git diff output.
    """
    # Validate argument combinations
    if input_file and (tests or sprint):
        click.echo("Error: cannot combine INPUT_FILE with --tests/--sprint flags.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if not input_file and not (tests and sprint):
        click.echo("Error: provide either INPUT_FILE or both --tests and --sprint.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if history_dir and history_file:
        click.echo("Error: --history-dir and --history-file are mutually exclusive.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if area_map and not (diff_file or ref):
        click.echo("Error: --area-map requires --diff-file or --ref.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if diff_file and ref:
        click.echo("Error: --diff-file and --ref are mutually exclusive.", err=True)
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

    # Resolve area map → changed_areas set (CLI layer owns git/file I/O)
    changed_areas: set[str] | None = None
    if area_map is not None:
        try:
            mappings = load_area_map(area_map)
        except InputValidationError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(EXIT_INPUT_ERROR)
        if diff_file:
            diff_p = Path(diff_file)
            if not diff_p.exists():
                click.echo(f"Error: diff file not found: {diff_file!r}", err=True)
                sys.exit(EXIT_INPUT_ERROR)
            diff_text = diff_p.read_text(encoding="utf-8")
        else:
            git_ref = ref
            proc = subprocess.run(
                ["git", "diff", "--name-only", git_ref],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                click.echo(f"Error: git diff failed (exit {proc.returncode})", err=True)
                sys.exit(EXIT_INPUT_ERROR)
            diff_text = proc.stdout
        files = parse_diff_output(diff_text)
        changed_areas = map_files_to_areas(files, mappings)

    if input_file:
        result = run_pipeline(input_file, history=history, changed_areas=changed_areas)
    else:
        # Merge mode — history applied inside run_pipeline_from_merged via separate helper
        result = _run_merged(tests, sprint, history=history, changed_areas=changed_areas)  # type: ignore[arg-type]

    if result.exit_code == EXIT_INPUT_ERROR:
        click.echo(f"Error: {result.message}", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if result.exit_code == EXIT_VALIDATION_ERROR:
        click.echo(f"Validation error: {result.message}", err=True)
        sys.exit(EXIT_VALIDATION_ERROR)

    for warning in result.warnings:
        click.echo(f"Warning: {warning}", err=True)

    # LLM mode routing — deterministic result is used for comparison and as fallback context
    if mode in ("llm", "compare"):
        cli_overrides: dict[str, Any] = {}
        if provider:
            cli_overrides["provider"] = provider
        if model:
            cli_overrides["model"] = model
        if base_url:
            cli_overrides["base_url"] = base_url
        if temperature is not None:
            cli_overrides["temperature"] = temperature
        if max_tokens is not None:
            cli_overrides["max_tokens"] = max_tokens

        try:
            llm_cfg = load_llm_config(config_path=llm_config, cli_overrides=cli_overrides)
        except (FileNotFoundError, ValueError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(EXIT_INPUT_ERROR)

        if llm_cfg.provider in ("openai", "gemini") and not llm_cfg.api_key:
            click.echo(
                f"Error: --mode {mode} with provider {llm_cfg.provider!r} requires IRO_LLM_API_KEY.",
                err=True,
            )
            sys.exit(EXIT_INPUT_ERROR)

        llm_client = create_llm_client(llm_cfg)

        # Re-derive normalized/classifications/tier_result for the LLM layer
        from .context_classifier import classify_context
        from .scoring_engine import score_tests
        from .input_loader import load_input

        if input_file:
            pkg = load_input(input_file)
            normalized = pkg.normalized
        else:
            # Merge mode: reconstruct from the two YAML files already validated above
            from .end_to_end_flow import merge_history
            from .input_loader import validate_raw
            merged_data = _read_and_merge_yaml(tests, sprint)  # type: ignore[arg-type]
            normalized = validate_raw(merged_data)
            if history:
                normalized, _ = merge_history(normalized, history)
            if changed_areas is not None:
                from .diff_mapper import apply_area_map
                normalized = apply_area_map(normalized, changed_areas)

        # Propagate history provenance so the LLM prompt can cite its data source
        if history is not None:
            normalized.setdefault("_meta", {})["history_source"] = "ci-history"

        classifications = classify_context(normalized)
        tier_result = score_tests(normalized, classifications)

        llm_result = run_llm_pipeline(normalized, classifications, tier_result, llm_client)

        if mode == "compare":
            from .comparison import build_comparison_report
            report = build_comparison_report(result.message, llm_result)
        else:
            report = llm_result.flow_result.message

        _emit(output, _maybe_summarise(report, summary_only))
        sys.exit(EXIT_OK)

    _emit(output, _maybe_summarise(result.message, summary_only))
    sys.exit(EXIT_OK)


def _maybe_summarise(content: str, summary_only: bool) -> str:
    """Return only the Optimisation Summary section when summary_only is set."""
    if not summary_only:
        return content
    import re
    match = re.search(
        r"(## Optimisation Summary.*?)(?=\n## |\Z)", content, re.DOTALL
    )
    return match.group(1).rstrip() + "\n" if match else content


def _emit(output: str | None, content: str) -> None:
    """Write content to file or stdout."""
    if output:
        Path(output).write_text(content, encoding="utf-8")
    else:
        click.echo(content)


def _run_merged(
    tests_path: str,
    sprint_path: str,
    history: dict | None = None,
    changed_areas: set | None = None,
) -> Any:
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

    return run_pipeline_from_merged(merged, history=history, changed_areas=changed_areas)


def _read_and_merge_yaml(tests_path: str, sprint_path: str) -> dict[str, Any]:
    """Read test_suite YAML and sprint YAML, merge into a combined input dict.

    Assumes both files exist and contain the expected keys.
    """
    with Path(tests_path).open(encoding="utf-8") as fh:
        tests_data = yaml.safe_load(fh)
    with Path(sprint_path).open(encoding="utf-8") as fh:
        sprint_data = yaml.safe_load(fh)
    return {
        "sprint_context": sprint_data["sprint_context"],
        "test_suite": tests_data["test_suite"],
        "constraints": sprint_data["constraints"],
    }


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


@main.command("diff-areas")
@click.option("--area-map", required=True, type=click.Path(),
              help="area-map.yaml config mapping glob patterns to coverage areas.")
@click.option("--diff-file", type=click.Path(), default=None,
              help="File containing 'git diff --name-only' output.")
@click.option("--ref", type=str, default=None,
              help="Git ref to diff against, e.g. HEAD~1. Runs 'git diff --name-only <ref>'. Required unless --diff-file is given.")
def diff_areas(area_map: str, diff_file: str | None, ref: str | None) -> None:
    """Derive changed_areas from git diff and print a YAML fragment.

    Output: 'changed_areas: [Area1, Area2]' — paste into sprint_context.stories.
    """
    if diff_file and ref:
        click.echo("Error: --diff-file and --ref are mutually exclusive.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if not diff_file and not ref:
        click.echo("Error: provide --diff-file or --ref.", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    try:
        mappings = load_area_map(area_map)
    except InputValidationError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_INPUT_ERROR)

    if diff_file:
        diff_p = Path(diff_file)
        if not diff_p.exists():
            click.echo(f"Error: diff file not found: {diff_file!r}", err=True)
            sys.exit(EXIT_INPUT_ERROR)
        diff_text = diff_p.read_text(encoding="utf-8")
    else:
        git_ref = ref
        proc = subprocess.run(
            ["git", "diff", "--name-only", git_ref],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            click.echo(f"Error: git diff failed (exit {proc.returncode})", err=True)
            sys.exit(EXIT_INPUT_ERROR)
        diff_text = proc.stdout

    files = parse_diff_output(diff_text)
    areas = map_files_to_areas(files, mappings)
    fragment = yaml.dump(
        {"changed_areas": sorted(areas)},
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    click.echo(fragment, nl=False)
    sys.exit(EXIT_OK)


# ---------------------------------------------------------------------------
# init command — template YAML generator
# ---------------------------------------------------------------------------

import textwrap as _textwrap

_PLAIN_SCAFFOLD = _textwrap.dedent("""\
    # TODO: Fill in the sprint context below
    sprint_context:
      sprint_goal: "TODO: Describe the sprint goal"
      stories:
        - id: TODO_story_id  # TODO: unique story identifier
          summary: "TODO: Story summary"
          risk: high  # TODO: one of: high | medium | low
          changed_areas: []  # TODO: list of changed areas

    # TODO: Define the tests to consider for this sprint
    test_suite:
      - id: TODO_test_id
        name: "TODO: human readable test name"
        layer: unit  # TODO: one of: unit | integration | e2e | security | performance
        coverage_areas: [TODO_area]  # TODO: list of areas this test covers
        execution_time_secs: 0  # TODO: average execution time in seconds
        flakiness_rate: 0.0     # TODO: fraction of runs that were flaky

    # TODO: Define optimisation constraints
    constraints:
      time_budget_mins: 5       # TODO: execution budget in minutes
      mandatory_tags: []        # TODO: tags that force must-run
      flakiness_retire_threshold: 0.30   # TODO: retire threshold
      flakiness_high_tier_threshold: 0.20  # TODO: high-flakiness threshold
""")


@main.command("init")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Write template YAML to this file instead of stdout.")
@click.option("--from-junit", "from_junit", type=click.Path(), default=None,
              help="Directory of JUnit XML files to pre-populate the template.")
def init(output: str | None, from_junit: str | None) -> None:
    """Generate a template YAML input file for 'iro run'."""
    import collections as _collections
    import xml.etree.ElementTree as _ET

    if from_junit is not None:
        junit_path = Path(from_junit)
        if not junit_path.is_dir():
            click.echo(f"Error: --from-junit directory not found: {from_junit!r}", err=True)
            sys.exit(EXIT_INPUT_ERROR)

        xml_files = sorted(junit_path.glob("*.xml"))
        times_acc: dict[str, list[float]] = _collections.defaultdict(list)
        names_map: dict[str, str] = {}

        for xml_file in xml_files:
            try:
                tree = _ET.parse(xml_file)
            except _ET.ParseError as exc:
                click.echo(f"Error: malformed XML {xml_file.name!r}: {exc}", err=True)
                sys.exit(EXIT_INPUT_ERROR)
            root = tree.getroot()
            if root.tag == "testsuites":
                suites = list(root.findall("testsuite"))
            elif root.tag == "testsuite":
                suites = [root]
            else:
                suites = list(root.iter("testsuite"))
            for suite in suites:
                for tc in suite.findall("testcase"):
                    if tc.find("skipped") is not None:
                        continue
                    name = tc.get("name") or ""
                    classname = tc.get("classname") or None
                    test_id = f"{classname}::{name}" if classname else name
                    time_str = tc.get("time") or "0"
                    try:
                        t = float(time_str)
                    except ValueError:
                        t = 0.0
                    times_acc[test_id].append(t)
                    if test_id not in names_map:
                        names_map[test_id] = name

        history = parse_junit_directory(from_junit)

        test_entries = []
        for test_id in sorted(times_acc):
            avg_time = sum(times_acc[test_id]) / len(times_acc[test_id])
            exec_time_int = max(1, round(avg_time))
            flakiness_rec = history.get(test_id)
            flakiness_rate = round(flakiness_rec.flakiness_rate, 4) if flakiness_rec else 0.0
            test_entries.append({
                "id": test_id,
                "name": names_map.get(test_id, test_id),
                "layer": "TODO",
                "coverage_areas": ["UNKNOWN"],
                "execution_time_secs": exec_time_int,
                "flakiness_rate": flakiness_rate,
            })

        doc = {
            "sprint_context": {
                "sprint_goal": "TODO: Describe the sprint goal",
                "stories": [{"id": "TODO_story_id", "summary": "TODO: Story summary", "risk": "high", "changed_areas": []}],
            },
            "test_suite": test_entries,
            "constraints": {
                "time_budget_mins": 5,
                "mandatory_tags": [],
                "flakiness_retire_threshold": 0.30,
                "flakiness_high_tier_threshold": 0.20,
            },
        }
        raw = yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True)
        raw = raw.replace("layer: TODO", "layer: TODO  # TODO: one of unit | integration | e2e")

        _emit(output, raw)
        sys.exit(EXIT_OK)

    _emit(output, _PLAIN_SCAFFOLD)
    sys.exit(EXIT_OK)
