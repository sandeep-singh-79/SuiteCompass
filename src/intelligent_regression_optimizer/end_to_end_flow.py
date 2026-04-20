"""End-to-end pipeline for intelligent-regression-optimizer.

Wires: load_input → classify_context → score_tests → render_report → validate_output
"""
from __future__ import annotations

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
    from intelligent_regression_optimizer.context_classifier import classify_context
    from intelligent_regression_optimizer.scoring_engine import score_tests
    from intelligent_regression_optimizer.renderer import render_report
    from intelligent_regression_optimizer.output_validator import validate_output

    # 1. Load and validate input
    try:
        package = load_input(input_path)
    except FileNotFoundError as exc:
        return FlowResult(exit_code=EXIT_INPUT_ERROR, message=str(exc), output_path=None)
    except InputValidationError as exc:
        return FlowResult(exit_code=EXIT_INPUT_ERROR, message=str(exc), output_path=None)

    # 2. Classify context
    classifications = classify_context(package.normalized)

    # 3. Score tests
    tier_result = score_tests(package.normalized, classifications)

    # 4. Render report
    markdown = render_report(package.normalized, classifications, tier_result)

    # 5. Validate output contract
    validation = validate_output(markdown)
    if not validation.is_valid:
        return FlowResult(
            exit_code=EXIT_VALIDATION_ERROR,
            message=f"Output contract violated: {validation.errors}",
            output_path=None,
        )

    return FlowResult(exit_code=EXIT_OK, message=markdown, output_path=None)
