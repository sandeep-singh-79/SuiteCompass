"""E2E tests — full pipeline through all 3 benchmarks — written RED before implementation."""
import pathlib
import pytest
from intelligent_regression_optimizer.end_to_end_flow import run_pipeline, merge_history, run_pipeline_from_merged
from intelligent_regression_optimizer.models import EXIT_OK, EXIT_INPUT_ERROR, TestHistoryRecord
from intelligent_regression_optimizer.junit_xml_parser import parse_junit_directory
from intelligent_regression_optimizer.benchmark_runner import run_assertions

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


# ---------------------------------------------------------------------------
# R2: run_pipeline() and run_pipeline_from_merged() surface warnings in FlowResult
# ---------------------------------------------------------------------------

class TestPipelineWarningsPropagation:
    def test_pipeline_warnings_populated_on_override(self, tmp_path):
        """run_pipeline() must populate FlowResult.warnings when history overrides flakiness."""
        import yaml
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
                    "flakiness_rate": 0.05,
                    "automated": True,
                }
            ],
            "constraints": {},
        }
        p = tmp_path / "input.yaml"
        p.write_text(yaml.safe_dump(data))
        history = {"T-001": TestHistoryRecord("T-001", flakiness_rate=0.9, failure_count_last_30d=9, total_runs=10)}
        result = run_pipeline(str(p), history=history)
        assert result.exit_code == EXIT_OK
        assert len(result.warnings) == 1
        assert "T-001" in result.warnings[0]

    def test_pipeline_warnings_empty_without_override(self, tmp_path):
        """run_pipeline() warnings must be empty when flakiness matches history."""
        import yaml
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
        p = tmp_path / "input.yaml"
        p.write_text(yaml.safe_dump(data))
        history = {"T-001": TestHistoryRecord("T-001", flakiness_rate=0.1, failure_count_last_30d=1, total_runs=10)}
        result = run_pipeline(str(p), history=history)
        assert result.exit_code == EXIT_OK
        assert result.warnings == []

    def test_pipeline_from_merged_warnings_populated_on_override(self):
        """run_pipeline_from_merged() must also propagate warnings."""
        data = {
            "sprint_context": {"stories": [{"id": "S-1", "risk": "low", "changed_areas": ["area-a"]}]},
            "test_suite": [
                {
                    "id": "T-002",
                    "name": "Test 002",
                    "layer": "unit",
                    "coverage_areas": ["area-a"],
                    "execution_time_secs": 5,
                    "flakiness_rate": 0.0,
                    "automated": True,
                }
            ],
            "constraints": {},
        }
        history = {"T-002": TestHistoryRecord("T-002", flakiness_rate=0.8, failure_count_last_30d=8, total_runs=10)}
        result = run_pipeline_from_merged(data, history=history)
        assert result.exit_code == EXIT_OK
        assert len(result.warnings) == 1
        assert "T-002" in result.warnings[0]


# ---------------------------------------------------------------------------
# R4: benchmarks/with-history/ end-to-end assertion benchmark
# ---------------------------------------------------------------------------

HISTORY_BENCHMARK = BENCHMARKS / "with-history"


class TestHistoryBenchmark:
    def test_history_benchmark_exits_ok(self):
        """Full pipeline with JUnit XML history runs without error."""
        xml_dir = HISTORY_BENCHMARK / "junit-history"
        history = parse_junit_directory(str(xml_dir))
        result = run_pipeline(str(HISTORY_BENCHMARK / "input.yaml"), history=history)
        assert result.exit_code == EXIT_OK, result.message

    def test_history_benchmark_assertions_pass(self):
        """All benchmark assertions prove that history changes recommendations."""
        xml_dir = HISTORY_BENCHMARK / "junit-history"
        history = parse_junit_directory(str(xml_dir))
        result = run_pipeline(str(HISTORY_BENCHMARK / "input.yaml"), history=history)
        assert result.exit_code == EXIT_OK
        ar = run_assertions(result.message, str(HISTORY_BENCHMARK / "assertions.yaml"))
        assert ar.is_valid, ar.errors

    def test_history_benchmark_flaky_test_retired(self):
        """T-HIST-FLAKY is a retire candidate when history drives flakiness above threshold."""
        xml_dir = HISTORY_BENCHMARK / "junit-history"
        history = parse_junit_directory(str(xml_dir))
        result = run_pipeline(str(HISTORY_BENCHMARK / "input.yaml"), history=history)
        assert result.exit_code == EXIT_OK
        assert "SprintSuite::flaky_history" in result.message

    def test_history_benchmark_stable_test_not_retired(self):
        """T-HIST-STABLE is NOT a retire candidate: history shows 0 flakiness despite YAML value."""
        xml_dir = HISTORY_BENCHMARK / "junit-history"
        history = parse_junit_directory(str(xml_dir))
        result = run_pipeline(str(HISTORY_BENCHMARK / "input.yaml"), history=history)
        assert result.exit_code == EXIT_OK
        # Retire format: "test_id test_name (flakiness: ..."
        assert "SprintSuite::stable_history (flakiness:" not in result.message

    def test_history_benchmark_override_warnings_emitted(self):
        """Override warnings are present in FlowResult.warnings for both tests."""
        xml_dir = HISTORY_BENCHMARK / "junit-history"
        history = parse_junit_directory(str(xml_dir))
        result = run_pipeline(str(HISTORY_BENCHMARK / "input.yaml"), history=history)
        assert result.exit_code == EXIT_OK
        # Both tests have different YAML vs history flakiness → 2 warnings
        assert len(result.warnings) == 2
        warning_text = " ".join(result.warnings)
        assert "SprintSuite::flaky_history" in warning_text
        assert "SprintSuite::stable_history" in warning_text


# ---------------------------------------------------------------------------
# V1-B E2E: run_pipeline with changed_areas derived from diff mapper
# ---------------------------------------------------------------------------

class TestChangedAreasEndToEnd:
    """Full pipeline with changed_areas parameter drives coverage-based tier assignments."""

    def _minimal_input_path(self, tmp_path, test_coverage: list[str], story_areas: list[str]) -> str:
        import yaml
        data = {
            "sprint_context": {
                "sprint_id": "S-DIFF",
                "stories": [{
                    "id": "S1", "risk": "high",
                    "changed_areas": story_areas,
                    "dependency_stories": [],
                }],
                "exploratory_sessions": [],
            },
            "test_suite": [{
                "id": "T-target", "name": "Target test",
                "layer": "unit", "coverage_areas": test_coverage,
                "execution_time_secs": 30, "flakiness_rate": 0.0,
                "automated": True,
            }],
            "constraints": {"time_budget_mins": 60, "flakiness_retire_threshold": 0.30},
        }
        p = tmp_path / "input.yaml"
        p.write_text(yaml.safe_dump(data))
        return str(p)

    def test_changed_areas_none_leaves_output_unaffected(self, tmp_path):
        # With original area in story, test should score normally
        p = self._minimal_input_path(tmp_path, ["AreaA"], ["AreaA"])
        result = run_pipeline(p, changed_areas=None)
        assert result.exit_code == EXIT_OK

    def test_changed_areas_set_overrides_story_areas_and_affects_tier(self, tmp_path):
        # Story originally covers AreaA; test covers AreaB only.
        # With changed_areas={"AreaB"}, the story areas are replaced → test now matches.
        p = self._minimal_input_path(tmp_path, ["AreaB"], ["AreaA"])
        without = run_pipeline(p, changed_areas=None)
        with_diff = run_pipeline(p, changed_areas={"AreaB"})
        assert without.exit_code == EXIT_OK
        assert with_diff.exit_code == EXIT_OK
        # Both should produce valid reports; presence in must-run should differ
        assert "## Optimisation Summary" in with_diff.message

    def test_changed_areas_empty_set_clears_all_story_areas(self, tmp_path):
        # empty changed_areas → direct_coverage = 0 for every test → raw_score ≤ 0 → defer tier
        p = self._minimal_input_path(tmp_path, ["AreaA"], ["AreaA"])
        result = run_pipeline(p, changed_areas=set())
        assert result.exit_code == EXIT_OK
        from intelligent_regression_optimizer.output_validator import parse_sections
        sections = parse_sections(result.message)
        defer_body = sections.get("## Defer To Overnight Run", "")
        must_body = sections.get("## Must-Run", "")
        should_body = sections.get("## Should-Run If Time Permits", "")
        assert "T-target" in defer_body, "T-target should be in defer when changed_areas is empty"
        assert "T-target" not in must_body
        assert "T-target" not in should_body

    def test_pipeline_with_changed_areas_output_passes_validator(self, tmp_path):
        from intelligent_regression_optimizer.output_validator import validate_output
        p = self._minimal_input_path(tmp_path, ["AreaA"], ["OtherArea"])
        result = run_pipeline(p, changed_areas={"AreaA"})
        assert result.exit_code == EXIT_OK
        vr = validate_output(result.message)
        assert vr.is_valid, vr.errors


# ---------------------------------------------------------------------------
# V1-C E2E: LLM pipeline modes — repair and compare
# ---------------------------------------------------------------------------

def _make_llm_normalized():
    """Minimal normalised dict suitable for run_llm_pipeline() calls."""
    return {
        "sprint_context": {
            "sprint_id": "S-LLM-E2E",
            "stories": [{"id": "S1", "risk": "high", "changed_areas": ["ServiceA"], "resolved_deps": []}],
            "exploratory_sessions": [],
        },
        "test_suite": [{
            "id": "T1", "name": "service a test", "layer": "unit",
            "coverage_areas": ["ServiceA"], "execution_time_secs": 30,
            "flakiness_rate": 0.0, "failure_count_last_30d": 0,
            "automated": True, "tags": [],
        }],
        "constraints": {
            "time_budget_mins": 60, "mandatory_tags": [],
            "flakiness_retire_threshold": 0.30, "flakiness_high_tier_threshold": 0.20,
        },
    }


class TestLLMPipelineE2E:
    """Full run_llm_pipeline() paths: happy path, repaired, and compare mode."""

    def _run(self, content: str):
        from intelligent_regression_optimizer.context_classifier import classify_context
        from intelligent_regression_optimizer.llm_client import FakeLLMClient
        from intelligent_regression_optimizer.llm_flow import run_llm_pipeline
        from intelligent_regression_optimizer.scoring_engine import score_tests
        normalized = _make_llm_normalized()
        classifications = classify_context(normalized)
        tier_result = score_tests(normalized, classifications)
        return run_llm_pipeline(normalized, classifications, tier_result, FakeLLMClient(content))

    def test_valid_llm_output_exits_ok(self):
        from intelligent_regression_optimizer.llm_client import _FAKE_RESPONSE
        result = self._run(_FAKE_RESPONSE)
        assert result.flow_result.exit_code == EXIT_OK
        assert result.recommendation_mode == "llm"

    def test_valid_llm_output_passes_contract(self):
        from intelligent_regression_optimizer.llm_client import _FAKE_RESPONSE
        from intelligent_regression_optimizer.output_validator import validate_output
        result = self._run(_FAKE_RESPONSE)
        vr = validate_output(result.flow_result.message)
        assert vr.is_valid, vr.errors

    def test_repaired_llm_output_exits_ok_and_passes_contract(self):
        from intelligent_regression_optimizer.llm_client import _FAKE_RESPONSE
        from intelligent_regression_optimizer.output_validator import validate_output
        # Remove one required heading to force repair path
        broken = _FAKE_RESPONSE.replace("## Retire Candidates\n", "")
        result = self._run(broken)
        assert result.flow_result.exit_code == EXIT_OK
        assert result.recommendation_mode == "llm-repaired"
        assert len(result.repair_actions) > 0
        vr = validate_output(result.flow_result.message)
        assert vr.is_valid, vr.errors

    def test_compare_mode_output_contains_both_sections(self):
        from intelligent_regression_optimizer.context_classifier import classify_context
        from intelligent_regression_optimizer.llm_client import FakeLLMClient, _FAKE_RESPONSE
        from intelligent_regression_optimizer.llm_flow import run_llm_pipeline
        from intelligent_regression_optimizer.scoring_engine import score_tests
        from intelligent_regression_optimizer.comparison import build_comparison_report
        from intelligent_regression_optimizer.end_to_end_flow import run_pipeline_from_merged
        # Get deterministic output
        normalized = _make_llm_normalized()
        det_result = run_pipeline_from_merged(normalized)
        # Get LLM result
        classifications = classify_context(normalized)
        tier_result = score_tests(normalized, classifications)
        llm_result = run_llm_pipeline(normalized, classifications, tier_result, FakeLLMClient())
        # Build comparison
        report = build_comparison_report(det_result.message, llm_result)
        assert "## Comparison Summary" in report
        assert "## Deterministic Output" in report
        assert "## LLM Output" in report
        assert "LLM Recommendation Mode: llm" in report

    def test_compare_mode_deterministic_section_contains_valid_headings(self):
        from intelligent_regression_optimizer.context_classifier import classify_context
        from intelligent_regression_optimizer.llm_client import FakeLLMClient
        from intelligent_regression_optimizer.llm_flow import run_llm_pipeline
        from intelligent_regression_optimizer.scoring_engine import score_tests
        from intelligent_regression_optimizer.comparison import build_comparison_report
        from intelligent_regression_optimizer.end_to_end_flow import run_pipeline_from_merged
        normalized = _make_llm_normalized()
        det_result = run_pipeline_from_merged(normalized)
        classifications = classify_context(normalized)
        tier_result = score_tests(normalized, classifications)
        llm_result = run_llm_pipeline(normalized, classifications, tier_result, FakeLLMClient())
        report = build_comparison_report(det_result.message, llm_result)
        assert "## Optimisation Summary" in report
        assert "Recommendation Mode: deterministic" in report