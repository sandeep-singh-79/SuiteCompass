"""Output contract compliance tests — all benchmarks must pass validator and assertion files."""
import pathlib
import pytest
from intelligent_regression_optimizer.end_to_end_flow import run_pipeline
from intelligent_regression_optimizer.benchmark_runner import run_assertions
from intelligent_regression_optimizer.output_validator import validate_output

BENCHMARKS = pathlib.Path(__file__).parent.parent / "benchmarks"

BENCHMARK_PAIRS = [
    ("high-risk-feature-sprint.input.yaml", "high-risk-feature-sprint.assertions.yaml"),
    ("low-risk-bugfix-sprint.input.yaml", "low-risk-bugfix-sprint.assertions.yaml"),
    ("degraded-suite-high-flakiness.input.yaml", "degraded-suite-high-flakiness.assertions.yaml"),
]


class TestOutputContractCompliance:
    @pytest.mark.parametrize("input_file,_", BENCHMARK_PAIRS)
    def test_benchmark_output_passes_validator(self, input_file, _):
        result = run_pipeline(str(BENCHMARKS / input_file))
        vr = validate_output(result.message)
        assert vr.is_valid, f"{input_file}: {vr.errors}"

    @pytest.mark.parametrize("input_file,assertions_file", BENCHMARK_PAIRS)
    def test_benchmark_passes_all_assertions(self, input_file, assertions_file):
        result = run_pipeline(str(BENCHMARKS / input_file))
        ar = run_assertions(result.message, str(BENCHMARKS / assertions_file))
        assert ar.is_valid, f"{input_file}: {ar.errors}"
