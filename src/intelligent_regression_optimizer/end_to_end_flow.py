"""End-to-end pipeline for intelligent-regression-optimizer.

Wires: load_input → classify_context → score_tests → render_report → validate_output
"""
from __future__ import annotations

from typing import Any

from intelligent_regression_optimizer.models import (
    EXIT_INPUT_ERROR,
    EXIT_OK,
    EXIT_VALIDATION_ERROR,
    FlowResult,
)


def run_pipeline(input_path: str) -> FlowResult:
    """Run the full deterministic pipeline on *input_path*.

    Args:
        input_path: Path to the input YAML file.

    Returns:
        :class:`FlowResult` with exit_code and the rendered markdown in
        ``message`` (or an error description on failure).
    """
    from intelligent_regression_optimizer.input_loader import (
        InputValidationError,
        load_input,
    )

    # 1. Load and validate input
    try:
        package = load_input(input_path)
    except FileNotFoundError as exc:
        return FlowResult(exit_code=EXIT_INPUT_ERROR, message=str(exc), output_path=None)
    except InputValidationError as exc:
        return FlowResult(exit_code=EXIT_INPUT_ERROR, message=str(exc), output_path=None)

    return _run_from_package(package.normalized)


def run_pipeline_from_merged(data: dict[str, Any]) -> FlowResult:
    """Run the pipeline on an already-merged and validated input dict.

    Used by the CLI merge utility when sprint context and test suite are
    supplied as separate files.

    Args:
        data: A dict containing sprint_context, test_suite, and constraints.

    Returns:
        :class:`FlowResult` with exit_code and the rendered markdown in
        ``message`` (or an error description on failure).
    """
    from intelligent_regression_optimizer.input_loader import (
        InputValidationError,
        validate_raw,
    )

    try:
        normalized = validate_raw(data)
    except InputValidationError as exc:
        return FlowResult(exit_code=EXIT_INPUT_ERROR, message=str(exc), output_path=None)

    return _run_from_package(normalized)


def _run_from_package(normalized: dict[str, Any]) -> FlowResult:
    """Shared pipeline logic: classify → score → render → validate."""
    from intelligent_regression_optimizer.context_classifier import classify_context
    from intelligent_regression_optimizer.scoring_engine import score_tests
    from intelligent_regression_optimizer.renderer import render_report
    from intelligent_regression_optimizer.output_validator import validate_output

    # Classify context
    classifications = classify_context(normalized)

    # Score tests
    tier_result = score_tests(normalized, classifications)

    # Render report
    markdown = render_report(normalized, classifications, tier_result)

    # Validate output contract
    validation = validate_output(markdown)
    if not validation.is_valid:
        return FlowResult(
            exit_code=EXIT_VALIDATION_ERROR,
            message=f"Output contract violated: {validation.errors}",
            output_path=None,
        )

    return FlowResult(exit_code=EXIT_OK, message=markdown, output_path=None)
