"""E2E tests — full pipeline through all 3 benchmarks — written RED before implementation."""
import pathlib
import pytest
from intelligent_regression_optimizer.end_to_end_flow import run_pipeline
from intelligent_regression_optimizer.models import EXIT_OK, EXIT_INPUT_ERROR

BENCHMARKS = pathlib.Path(__file__).parent.parent / "benchmarks"
TMP = pathlib.Path(__file__).parent.parent / "tmp"


class TestBenchmarkEndToEnd:
    def test_high_risk_benchmark_exits_ok(self):
        result = run_pipeline(str(BENCHMARKS / "high-risk-feature-sprint.input.yaml"))
        assert result.exit_code == EXIT_OK

    def test_low_risk_benchmark_exits_ok(self):
        result = run_pipeline(str(BENCHMARKS / "low-risk-bugfix-sprint.input.yaml"))
        assert result.exit_code == EXIT_OK

    def test_degraded_suite_benchmark_exits_ok(self):
        result = run_pipeline(str(BENCHMARKS / "degraded-suite-high-flakiness.input.yaml"))
        assert result.exit_code == EXIT_OK

    def test_high_risk_output_passes_validator(self):
        from intelligent_regression_optimizer.output_validator import validate_output
        result = run_pipeline(str(BENCHMARKS / "high-risk-feature-sprint.input.yaml"))
        vr = validate_output(result.message)
        assert vr.is_valid, vr.errors

    def test_invalid_input_returns_exit_input_error(self):
        result = run_pipeline("/nonexistent/path/input.yaml")
        assert result.exit_code == EXIT_INPUT_ERROR
