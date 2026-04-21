"""End-to-end pipeline for intelligent-regression-optimizer.

Wires: load_input → (merge_history) → classify_context → score_tests → render_report → validate_output
"""
from __future__ import annotations

from typing import Any

from intelligent_regression_optimizer.models import (
    EXIT_INPUT_ERROR,
    EXIT_OK,
    EXIT_VALIDATION_ERROR,
    FlowResult,
    TestHistoryRecord,
)


# ---------------------------------------------------------------------------
# History merge
# ---------------------------------------------------------------------------

def merge_history(
    normalized: dict[str, Any],
    history: dict[str, TestHistoryRecord],
) -> tuple[dict[str, Any], list[str]]:
    """Overlay history-derived metrics onto the test_suite in *normalized*.

    For each test whose ID is found in *history*:

    - ``flakiness_rate`` is replaced by the history-computed value.
    - ``failure_count_last_30d`` and ``total_runs`` are added from the record.

    When the existing YAML ``flakiness_rate`` differs from the history value,
    a human-readable warning string is appended to the returned list.

    This function does **not** mutate *normalized* — it returns a new dict.

    Args:
        normalized: Validated and normalised input dict from :func:`load_input`.
        history: Mapping of test_id → :class:`TestHistoryRecord`.

    Returns:
        Tuple of ``(updated_normalized, warnings)``.
    """
    if not history:
        return normalized, []

    warnings: list[str] = []
    updated_tests: list[dict] = []

    for test in normalized.get("test_suite", []):
        record = history.get(test["id"])
        if record is None:
            updated_tests.append(test)
            continue

        yaml_flakiness: float = test.get("flakiness_rate", 0.0)
        hist_flakiness: float = record.flakiness_rate

        if abs(yaml_flakiness - hist_flakiness) > 1e-9:
            warnings.append(
                f"[history-override] test_id={test['id']!r}: "
                f"flakiness_rate {yaml_flakiness:.3f} \u2192 {hist_flakiness:.3f} "
                f"(history wins)"
            )

        updated_tests.append({
            **test,
            "flakiness_rate": hist_flakiness,
            "failure_count_last_30d": record.failure_count_last_30d,
            "total_runs": record.total_runs,
        })

    updated_normalized = {
        **normalized,
        "test_suite": updated_tests,
    }
    return updated_normalized, warnings


# ---------------------------------------------------------------------------
# Pipeline entry points
# ---------------------------------------------------------------------------

def run_pipeline(
    input_path: str,
    history: dict[str, TestHistoryRecord] | None = None,
    changed_areas: set[str] | None = None,
) -> FlowResult:
    """Run the full deterministic pipeline on *input_path*.

    Args:
        input_path: Path to the input YAML file.
        history: Optional pre-loaded history mapping (test_id → record).
            When supplied, history values are merged onto the YAML test_suite
            before the scoring pipeline runs.

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

    normalized = package.normalized

    # 2. Overlay history when provided
    if history:
        normalized, _ = merge_history(normalized, history)

    # 3. Override changed_areas when derived from diff
    if changed_areas is not None:
        from intelligent_regression_optimizer.diff_mapper import apply_area_map
        normalized = apply_area_map(normalized, changed_areas)

    return _run_from_package(normalized)


def run_pipeline_from_merged(
    data: dict[str, Any],
    history: dict[str, TestHistoryRecord] | None = None,
    changed_areas: set[str] | None = None,
) -> FlowResult:
    """Run the pipeline on an already-merged and validated input dict.

    Args:
        data: A dict containing sprint_context, test_suite, and constraints.
        history: Optional pre-loaded history mapping (test_id → record).

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

    if history:
        normalized, _ = merge_history(normalized, history)

    if changed_areas is not None:
        from intelligent_regression_optimizer.diff_mapper import apply_area_map
        normalized = apply_area_map(normalized, changed_areas)

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
