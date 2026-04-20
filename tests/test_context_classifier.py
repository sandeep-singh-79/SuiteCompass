"""Unit tests for context_classifier.py — written RED before implementation."""
import pytest
from intelligent_regression_optimizer.context_classifier import classify_context


def _make_normalized(stories: list[dict], tests: list[dict], budget_mins: int = 30,
                     exploratory: list[dict] | None = None) -> dict:
    return {
        "sprint_context": {
            "sprint_id": "S-TEST",
            "stories": [
                {**s, "resolved_deps": s.get("resolved_deps", [])}
                for s in stories
            ],
            "exploratory_sessions": exploratory or [],
        },
        "test_suite": tests,
        "constraints": {
            "time_budget_mins": budget_mins,
            "mandatory_tags": [],
            "flakiness_retire_threshold": 0.30,
            "flakiness_high_tier_threshold": 0.20,
        },
    }


def _story(id_: str, risk: str) -> dict:
    return {"id": id_, "risk": risk, "changed_areas": ["Area"], "resolved_deps": []}


def _test(id_: str, layer: str = "unit", flakiness: float = 0.01,
          exec_secs: int = 10, failures: int = 0) -> dict:
    return {
        "id": id_,
        "name": f"test {id_}",
        "layer": layer,
        "coverage_areas": ["Area"],
        "execution_time_secs": exec_secs,
        "flakiness_rate": flakiness,
        "failure_count_last_30d": failures,
        "automated": True,
        "tags": [],
    }


# ---------------------------------------------------------------------------
# Sprint risk level
# ---------------------------------------------------------------------------

class TestSprintRiskLevel:
    def test_high_risk_story_sets_sprint_risk_high(self):
        normalized = _make_normalized([_story("S1", "high")], [_test("T1")])
        result = classify_context(normalized)
        assert result["sprint_risk_level"] == "high"

    def test_medium_risk_only_sets_sprint_risk_medium(self):
        normalized = _make_normalized([_story("S1", "medium"), _story("S2", "low")], [_test("T1")])
        result = classify_context(normalized)
        assert result["sprint_risk_level"] == "medium"

    def test_low_risk_only_sets_sprint_risk_low(self):
        normalized = _make_normalized([_story("S1", "low")], [_test("T1")])
        result = classify_context(normalized)
        assert result["sprint_risk_level"] == "low"

    def test_mixed_high_and_medium_returns_high(self):
        normalized = _make_normalized([_story("S1", "medium"), _story("S2", "high")], [_test("T1")])
        result = classify_context(normalized)
        assert result["sprint_risk_level"] == "high"

    def test_no_stories_returns_low(self):
        normalized = _make_normalized([], [_test("T1")])
        result = classify_context(normalized)
        assert result["sprint_risk_level"] == "low"


# ---------------------------------------------------------------------------
# NFR elevation
# ---------------------------------------------------------------------------

class TestNfrElevation:
    def test_nfr_elevation_true_when_sprint_risk_high(self):
        normalized = _make_normalized([_story("S1", "high")], [_test("T1")])
        result = classify_context(normalized)
        assert result["nfr_elevation_required"] is True

    def test_nfr_elevation_false_when_sprint_risk_medium(self):
        normalized = _make_normalized([_story("S1", "medium")], [_test("T1")])
        result = classify_context(normalized)
        assert result["nfr_elevation_required"] is False

    def test_nfr_elevation_false_when_sprint_risk_low(self):
        normalized = _make_normalized([_story("S1", "low")], [_test("T1")])
        result = classify_context(normalized)
        assert result["nfr_elevation_required"] is False


# ---------------------------------------------------------------------------
# Suite health
# ---------------------------------------------------------------------------

class TestSuiteHealth:
    def test_suite_health_degraded_above_20pct_flaky(self):
        # 3 of 10 tests (30%) above 0.20 threshold → degraded
        tests = [_test(f"T{i}", flakiness=0.25) for i in range(3)] + \
                [_test(f"T{i+3}", flakiness=0.01) for i in range(7)]
        normalized = _make_normalized([_story("S1", "low")], tests)
        result = classify_context(normalized)
        assert result["suite_health"] == "degraded"

    def test_suite_health_stable_below_5pct_flaky(self):
        # 0 of 10 tests above 0.20 → stable
        tests = [_test(f"T{i}", flakiness=0.01) for i in range(10)]
        normalized = _make_normalized([_story("S1", "low")], tests)
        result = classify_context(normalized)
        assert result["suite_health"] == "stable"

    def test_suite_health_moderate_in_between(self):
        # 1 of 10 (10%) above threshold → moderate
        tests = [_test("T0", flakiness=0.25)] + \
                [_test(f"T{i+1}", flakiness=0.01) for i in range(9)]
        normalized = _make_normalized([_story("S1", "low")], tests)
        result = classify_context(normalized)
        assert result["suite_health"] == "moderate"

    def test_empty_suite_returns_stable(self):
        normalized = _make_normalized([_story("S1", "low")], [])
        result = classify_context(normalized)
        assert result["suite_health"] == "stable"


# ---------------------------------------------------------------------------
# Time pressure
# ---------------------------------------------------------------------------

class TestTimePressure:
    def test_time_pressure_tight_above_3x_budget(self):
        # Budget 10 min, total suite = 31 min → 3.1× → tight
        tests = [_test(f"T{i}", exec_secs=620) for i in range(3)]  # 3×620s = 1860s = 31 min
        normalized = _make_normalized([_story("S1", "low")], tests, budget_mins=10)
        result = classify_context(normalized)
        assert result["time_pressure"] == "tight"

    def test_time_pressure_relaxed_below_1_5x_budget(self):
        # Budget 60 min, total = 30 min → 0.5× → relaxed
        tests = [_test(f"T{i}", exec_secs=600) for i in range(3)]  # 3×600s = 30 min
        normalized = _make_normalized([_story("S1", "low")], tests, budget_mins=60)
        result = classify_context(normalized)
        assert result["time_pressure"] == "relaxed"

    def test_time_pressure_moderate_between_1_5x_and_3x(self):
        # Budget 20 min, total = 40 min → 2× → moderate
        tests = [_test(f"T{i}", exec_secs=1200) for i in range(2)]  # 2×1200s = 40 min
        normalized = _make_normalized([_story("S1", "low")], tests, budget_mins=20)
        result = classify_context(normalized)
        assert result["time_pressure"] == "moderate"


# ---------------------------------------------------------------------------
# Per-test stability scores
# ---------------------------------------------------------------------------

class TestStabilityScores:
    def test_stability_score_zero_flakiness_and_failures(self):
        tests = [_test("T1", flakiness=0.0, failures=0)]
        normalized = _make_normalized([_story("S1", "low")], tests)
        result = classify_context(normalized)
        score = result["per_test_stability"]["T1"]
        assert score == pytest.approx(1.0)

    def test_stability_score_high_flakiness_reduces_score(self):
        tests = [_test("T1", flakiness=1.0, failures=0)]
        normalized = _make_normalized([_story("S1", "low")], tests)
        result = classify_context(normalized)
        score = result["per_test_stability"]["T1"]
        # 1.0 - (0.7 × 1.0 + 0.3 × min(0/10, 1)) = 1.0 - 0.7 = 0.3
        assert score == pytest.approx(0.3)

    def test_stability_score_high_failures_reduces_score(self):
        tests = [_test("T1", flakiness=0.0, failures=10)]
        normalized = _make_normalized([_story("S1", "low")], tests)
        result = classify_context(normalized)
        score = result["per_test_stability"]["T1"]
        # 1.0 - (0.7 × 0 + 0.3 × min(10/10, 1)) = 1.0 - 0.3 = 0.7
        assert score == pytest.approx(0.7)

    def test_stability_score_capped_at_zero(self):
        tests = [_test("T1", flakiness=1.0, failures=100)]
        normalized = _make_normalized([_story("S1", "low")], tests)
        result = classify_context(normalized)
        score = result["per_test_stability"]["T1"]
        assert score >= 0.0
