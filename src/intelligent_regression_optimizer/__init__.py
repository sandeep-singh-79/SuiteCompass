"""intelligent-regression-optimizer public API."""

from __future__ import annotations

from intelligent_regression_optimizer.end_to_end_flow import (
    run_pipeline,
    run_pipeline_from_merged,
)
from intelligent_regression_optimizer.input_loader import load_input
from intelligent_regression_optimizer.output_validator import validate_output
from intelligent_regression_optimizer.scoring_engine import score_tests

__version__ = "1.3.0"

__all__ = [
    "run_pipeline",
    "run_pipeline_from_merged",
    "score_tests",
    "validate_output",
    "load_input",
]
