"""Integration tests — cross-module invariants (classifier → scorer → renderer → validator).

Written alongside each module pair as they are connected.
T6 integration: classifier → scorer
T7 integration: scorer invariants
T8 integration: scorer → renderer → validator
"""
import pathlib
import pytest

from intelligent_regression_optimizer.input_loader import load_input
from intelligent_regression_optimizer.context_classifier import classify_context
from intelligent_regression_optimizer.scoring_engine import score_tests

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _normalized(stories, tests, budget_mins=60, mandatory_tags=None, exploratory=None):
    return {
        "sprint_context": {
            "sprint_id": "S-INTEG",
            "stories": [{**s, "resolved_deps": s.get("resolved_deps", [])} for s in stories],
            "exploratory_sessions": exploratory or [],
        },
        "test_suite": tests,
        "constraints": {
            "time_budget_mins": budget_mins,
            "mandatory_tags": mandatory_tags or [],
            "flakiness_retire_threshold": 0.30,
            "flakiness_high_tier_threshold": 0.20,
        },
    }


def _story(id_, risk, changed_areas):
    return {"id": id_, "risk": risk, "changed_areas": changed_areas, "resolved_deps": []}


def _test(id_, layer="unit", coverage_areas=None, flakiness=0.01, exec_secs=60,
          automated=True, tags=None):
    return {
        "id": id_, "name": f"test {id_}", "layer": layer,
        "coverage_areas": coverage_areas or ["AreaA"],
        "execution_time_secs": exec_secs, "flakiness_rate": flakiness,
        "failure_count_last_30d": 0, "automated": automated, "tags": tags or [],
    }


# ---------------------------------------------------------------------------
# T6 integration: classifier → scorer
# ---------------------------------------------------------------------------

class TestClassifierScorerInvariants:
    def test_nfr_elevation_from_classifier_produces_performance_in_must_run(self):
        # Classifier derives nfr_elevation=True for high-risk sprint
        # Scorer should put performance/security tests in must-run
        normalized = _normalized(
            [_story("S1", "high", ["ServiceA"])],
            [
                _test("T1", layer="performance", coverage_areas=["UnrelatedArea"]),
                _test("T2", layer="security", coverage_areas=["UnrelatedArea"]),
                _test("T3", layer="unit", coverage_areas=["UnrelatedArea"]),
            ]
        )
        classifications = classify_context(normalized)
        assert classifications["nfr_elevation_required"] is True
        result = score_tests(normalized, classifications)
        must_ids = {s.test_id for s in result.must_run}
        assert "T1" in must_ids
        assert "T2" in must_ids
        assert "T3" not in must_ids  # unit layer not elevated

    def test_medium_risk_sprint_no_nfr_elevation(self):
        normalized = _normalized(
            [_story("S1", "medium", ["ServiceA"])],
            [_test("T1", layer="performance", coverage_areas=["UnrelatedArea"])]
        )
        classifications = classify_context(normalized)
        assert classifications["nfr_elevation_required"] is False
        result = score_tests(normalized, classifications)
        # performance test should NOT be in must-run (no direct match, no override)
        assert not any(s.test_id == "T1" for s in result.must_run)

    def test_sprint_risk_high_propagates_to_scoring_multiplier(self):
        # High sprint risk → classifier sets sprint_risk_level=high
        # Sprint has one high-risk story covering ServiceA
        # T1 covers ServiceA, zero flakiness → should score exactly 10.0
        normalized = _normalized(
            [_story("S1", "high", ["ServiceA"])],
            [_test("T1", coverage_areas=["ServiceA"], flakiness=0.0)]
        )
        classifications = classify_context(normalized)
        assert classifications["sprint_risk_level"] == "high"
        result = score_tests(normalized, classifications)
        all_scored = result.must_run + result.should_run + result.defer
        t1 = next(s for s in all_scored if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# T7 integration: scoring invariants
# ---------------------------------------------------------------------------

class TestScoringInvariants:
    def test_all_retire_candidates_are_flaky_and_non_unique(self):
        # All retire candidates must satisfy: flaky > threshold AND no unique coverage
        normalized = _normalized(
            [_story("S1", "low", ["OtherArea"])],
            [
                _test("T1", coverage_areas=["SharedArea"], flakiness=0.35),
                _test("T2", coverage_areas=["SharedArea"], flakiness=0.35),
                _test("T3", coverage_areas=["UniqueArea"], flakiness=0.35),  # unique → not retired
                _test("T4", coverage_areas=["SharedArea"], flakiness=0.01),  # not flaky
            ]
        )
        classifications = classify_context(normalized)
        result = score_tests(normalized, classifications)
        for st in result.retire:
            test = next(t for t in normalized["test_suite"] if t["id"] == st.test_id)
            assert test["flakiness_rate"] > 0.30
            assert test.get("automated", True) is True
        # T3 (unique) and T4 (not flaky) must NOT be in retire
        retire_ids = {s.test_id for s in result.retire}
        assert "T3" not in retire_ids
        assert "T4" not in retire_ids

    def test_budget_overflow_flag_set_when_must_run_exceeds_budget(self):
        # 3 high-risk tests × 30 min = 90 min > 60 min budget
        normalized = _normalized(
            [_story("S1", "high", ["ServiceA"])],
            [_test(f"T{i}", coverage_areas=["ServiceA"], exec_secs=1800) for i in range(1, 4)],
            budget_mins=60
        )
        classifications = classify_context(normalized)
        result = score_tests(normalized, classifications)
        assert result.budget_overflow is True
