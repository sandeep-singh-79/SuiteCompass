"""E2E tests — full pipeline through all 3 benchmarks — written RED before implementation."""
import pathlib
import pytest
from intelligent_regression_optimizer.end_to_end_flow import run_pipeline, merge_history, run_pipeline_from_merged
from intelligent_regression_optimizer.models import EXIT_OK, EXIT_INPUT_ERROR, TestHistoryRecord

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_normalized(tests: list[dict]) -> dict:
    """Minimal normalised input dict with the given test entries."""
    return {
        "sprint_context": {
            "stories": [],
            "exploratory_sessions": [],
        },
        "test_suite": tests,
        "constraints": {},
    }


def _make_test(test_id: str, flakiness_rate: float = 0.1) -> dict:
    return {
        "id": test_id,
        "name": f"Test {test_id}",
        "layer": "unit",
        "coverage_areas": ["area-a"],
        "execution_time_secs": 5,
        "flakiness_rate": flakiness_rate,
        "automated": True,
    }


def _make_record(
    test_id: str,
    flakiness_rate: float = 0.5,
    failure_count_last_30d: int = 10,
    total_runs: int = 20,
) -> TestHistoryRecord:
    return TestHistoryRecord(
        test_id=test_id,
        flakiness_rate=flakiness_rate,
        failure_count_last_30d=failure_count_last_30d,
        total_runs=total_runs,
    )


# ---------------------------------------------------------------------------
# merge_history() — unit tests
# ---------------------------------------------------------------------------

class TestMergeHistory:
    def test_empty_history_returns_normalized_unchanged(self):
        normalized = _make_normalized([_make_test("T-001", 0.1)])
        updated, warnings = merge_history(normalized, {})
        assert updated["test_suite"][0]["flakiness_rate"] == pytest.approx(0.1)
        assert warnings == []

    def test_history_overlays_flakiness_rate(self):
        normalized = _make_normalized([_make_test("T-001", flakiness_rate=0.1)])
        history = {"T-001": _make_record("T-001", flakiness_rate=0.6)}
        updated, _ = merge_history(normalized, history)
        assert updated["test_suite"][0]["flakiness_rate"] == pytest.approx(0.6)

    def test_history_adds_failure_count_last_30d(self):
        normalized = _make_normalized([_make_test("T-001")])
        history = {"T-001": _make_record("T-001", failure_count_last_30d=7)}
        updated, _ = merge_history(normalized, history)
        assert updated["test_suite"][0]["failure_count_last_30d"] == 7

    def test_history_adds_total_runs(self):
        normalized = _make_normalized([_make_test("T-001")])
        history = {"T-001": _make_record("T-001", total_runs=42)}
        updated, _ = merge_history(normalized, history)
        assert updated["test_suite"][0]["total_runs"] == 42

    def test_test_absent_from_history_is_unchanged(self):
        normalized = _make_normalized([_make_test("T-001", flakiness_rate=0.2)])
        history = {"T-OTHER": _make_record("T-OTHER")}
        updated, _ = merge_history(normalized, history)
        t = updated["test_suite"][0]
        assert t["flakiness_rate"] == pytest.approx(0.2)
        assert "failure_count_last_30d" not in t
        assert "total_runs" not in t

    def test_warning_emitted_when_flakiness_differs(self):
        normalized = _make_normalized([_make_test("T-001", flakiness_rate=0.1)])
        history = {"T-001": _make_record("T-001", flakiness_rate=0.6)}
        _, warnings = merge_history(normalized, history)
        assert len(warnings) == 1
        assert "T-001" in warnings[0]
        assert "0.100" in warnings[0]
        assert "0.600" in warnings[0]

    def test_no_warning_when_flakiness_matches(self):
        normalized = _make_normalized([_make_test("T-001", flakiness_rate=0.5)])
        history = {"T-001": _make_record("T-001", flakiness_rate=0.5)}
        _, warnings = merge_history(normalized, history)
        assert warnings == []

    def test_multiple_tests_mixed_presence(self):
        """Two tests: T-001 in history, T-002 not."""
        normalized = _make_normalized([
            _make_test("T-001", flakiness_rate=0.1),
            _make_test("T-002", flakiness_rate=0.2),
        ])
        history = {"T-001": _make_record("T-001", flakiness_rate=0.7, failure_count_last_30d=3, total_runs=10)}
        updated, warnings = merge_history(normalized, history)
        t1 = next(t for t in updated["test_suite"] if t["id"] == "T-001")
        t2 = next(t for t in updated["test_suite"] if t["id"] == "T-002")
        assert t1["flakiness_rate"] == pytest.approx(0.7)
        assert t1["failure_count_last_30d"] == 3
        assert t1["total_runs"] == 10
        assert t2["flakiness_rate"] == pytest.approx(0.2)
        assert "failure_count_last_30d" not in t2

    def test_all_tests_overlaid(self):
        normalized = _make_normalized([
            _make_test("T-001", flakiness_rate=0.0),
            _make_test("T-002", flakiness_rate=0.0),
        ])
        history = {
            "T-001": _make_record("T-001", flakiness_rate=0.3),
            "T-002": _make_record("T-002", flakiness_rate=0.8),
        }
        updated, _ = merge_history(normalized, history)
        assert updated["test_suite"][0]["flakiness_rate"] == pytest.approx(0.3)
        assert updated["test_suite"][1]["flakiness_rate"] == pytest.approx(0.8)

    def test_original_normalized_not_mutated(self):
        """merge_history must not mutate its input."""
        normalized = _make_normalized([_make_test("T-001", flakiness_rate=0.1)])
        history = {"T-001": _make_record("T-001", flakiness_rate=0.9)}
        merge_history(normalized, history)
        assert normalized["test_suite"][0]["flakiness_rate"] == pytest.approx(0.1)
        assert "failure_count_last_30d" not in normalized["test_suite"][0]

    def test_warning_count_matches_differing_tests(self):
        normalized = _make_normalized([
            _make_test("T-001", flakiness_rate=0.1),
            _make_test("T-002", flakiness_rate=0.5),  # same as history → no warning
        ])
        history = {
            "T-001": _make_record("T-001", flakiness_rate=0.9),
            "T-002": _make_record("T-002", flakiness_rate=0.5),
        }
        _, warnings = merge_history(normalized, history)
        assert len(warnings) == 1
        assert "T-001" in warnings[0]

    def test_empty_test_suite_returns_empty(self):
        normalized = _make_normalized([])
        updated, warnings = merge_history(normalized, {"T-001": _make_record("T-001")})
        assert updated["test_suite"] == []
        assert warnings == []


# ---------------------------------------------------------------------------
# run_pipeline() with history parameter
# ---------------------------------------------------------------------------

class TestRunPipelineWithHistory:
    def test_pipeline_with_history_none_exits_ok(self):
        result = run_pipeline(str(BENCHMARKS / "high-risk-feature-sprint.input.yaml"), history=None)
        assert result.exit_code == EXIT_OK

    def test_pipeline_with_empty_history_exits_ok(self):
        result = run_pipeline(str(BENCHMARKS / "high-risk-feature-sprint.input.yaml"), history={})
        assert result.exit_code == EXIT_OK

    def test_pipeline_with_history_applies_overlay(self, tmp_path):
        """History-supplied flakiness_rate is used in the pipeline (retire threshold check)."""
        import yaml
        # Write a minimal input YAML with a test set to "safe" flakiness_rate
        data = {
            "sprint_context": {
                "stories": [{"id": "S-1", "risk": "low", "changed_areas": ["area-a"]}],
            },
            "test_suite": [
                {
                    "id": "T-flaky",
                    "name": "Flaky test",
                    "layer": "unit",
                    "coverage_areas": ["area-a"],
                    "execution_time_secs": 5,
                    "flakiness_rate": 0.05,  # low in YAML — below retire threshold
                    "automated": True,
                }
            ],
            "constraints": {"flakiness_retire_threshold": 0.30, "time_budget_mins": 60},
        }
        p = tmp_path / "input.yaml"
        p.write_text(yaml.safe_dump(data))
        # History says this test is highly flaky → should push it to retire tier
        history = {
            "T-flaky": TestHistoryRecord(
                test_id="T-flaky",
                flakiness_rate=0.95,  # above retire threshold
                failure_count_last_30d=19,
                total_runs=20,
            )
        }
        result = run_pipeline(str(p), history=history)
        assert result.exit_code == EXIT_OK
        # The output should mention the retire section
        assert "Retire" in result.message or "retire" in result.message.lower()


# ---------------------------------------------------------------------------
# run_pipeline_from_merged() with history (covers end_to_end_flow.py line 148)
# ---------------------------------------------------------------------------

class TestRunPipelineFromMergedWithHistory:
    def test_history_overlaid_in_merged_mode(self):
        """History supplied to run_pipeline_from_merged() is merged before scoring."""
        data = {
            "sprint_context": {
                "stories": [{"id": "S-1", "risk": "low", "changed_areas": ["area-a"]}],
            },
            "test_suite": [
                {
                    "id": "T-merged",
                    "name": "Merged test",
                    "layer": "unit",
                    "coverage_areas": ["area-a"],
                    "execution_time_secs": 5,
                    "flakiness_rate": 0.05,   # below retire threshold
                    "automated": True,
                }
            ],
            "constraints": {"flakiness_retire_threshold": 0.30, "time_budget_mins": 60},
        }
        history = {
            "T-merged": TestHistoryRecord(
                test_id="T-merged",
                flakiness_rate=0.95,   # above retire threshold
                failure_count_last_30d=19,
                total_runs=20,
            )
        }
        result = run_pipeline_from_merged(data, history=history)
        assert result.exit_code == EXIT_OK
        assert "retire" in result.message.lower() or "Retire" in result.message

    def test_merged_mode_without_history_exits_ok(self):
        data = {
            "sprint_context": {
                "stories": [{"id": "S-1", "risk": "low", "changed_areas": ["area-a"]}],
            },
            "test_suite": [
                {
                    "id": "T-001",
                    "name": "Test 001",
                    "layer": "unit",
                    "coverage_areas": ["area-a"],
                    "execution_time_secs": 5,
                    "flakiness_rate": 0.1,
                    "automated": True,
                }
            ],
            "constraints": {},
        }
        result = run_pipeline_from_merged(data)
        assert result.exit_code == EXIT_OK

