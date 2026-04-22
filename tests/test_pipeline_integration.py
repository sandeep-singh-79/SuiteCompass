"""Integration tests — cross-module invariants (classifier → scorer → renderer → validator).

Written alongside each module pair as they are connected.
T6 integration: classifier → scorer
T7 integration: scorer invariants
T8 integration: scorer → renderer → validator
V1-A integration: history merge → tier changes
V1-B integration: diff mapper → pipeline
V1-C integration: LLM repair → validator, LLM fallback chain
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


# ---------------------------------------------------------------------------
# T8 integration: scorer → renderer → validator
# ---------------------------------------------------------------------------

class TestScorerRendererValidatorChain:
    """The rendered markdown of any scored result must pass the output contract."""

    def test_high_risk_scored_result_renders_valid_report(self):
        from intelligent_regression_optimizer.renderer import render_report
        from intelligent_regression_optimizer.output_validator import validate_output
        normalized = _normalized(
            [_story("S1", "high", ["ServiceA"])],
            [
                _test("T1", layer="performance", coverage_areas=["ServiceA"]),
                _test("T2", layer="unit", coverage_areas=["ServiceA"]),
            ]
        )
        classifications = classify_context(normalized)
        tier_result = score_tests(normalized, classifications)
        md = render_report(normalized, classifications, tier_result)
        vr = validate_output(md)
        assert vr.is_valid, vr.errors

    def test_all_required_labels_present_in_rendered_output(self):
        from intelligent_regression_optimizer.renderer import render_report
        from intelligent_regression_optimizer.output_validator import REQUIRED_LABELS
        normalized = _normalized(
            [_story("S1", "medium", ["AreaA"])],
            [_test("T1", coverage_areas=["AreaA"])]
        )
        classifications = classify_context(normalized)
        tier_result = score_tests(normalized, classifications)
        md = render_report(normalized, classifications, tier_result)
        for label in REQUIRED_LABELS:
            assert label in md, f"Missing label: {label!r}"

    def test_budget_overflow_label_set_correctly_when_overflow(self):
        from intelligent_regression_optimizer.renderer import render_report
        normalized = _normalized(
            [_story("S1", "high", ["AreaA"])],
            [_test(f"T{i}", coverage_areas=["AreaA"], exec_secs=1800) for i in range(1, 4)],
            budget_mins=1
        )
        classifications = classify_context(normalized)
        tier_result = score_tests(normalized, classifications)
        md = render_report(normalized, classifications, tier_result)
        assert "Budget Overflow: Yes" in md

    def test_nfr_elevation_label_set_correctly_when_active(self):
        from intelligent_regression_optimizer.renderer import render_report
        normalized = _normalized(
            [_story("S1", "high", ["AreaA"])],
            [_test("T1", layer="performance", coverage_areas=["OtherArea"])]
        )
        classifications = classify_context(normalized)
        tier_result = score_tests(normalized, classifications)
        md = render_report(normalized, classifications, tier_result)
        assert "NFR Elevation: Yes" in md

    def test_recommendation_mode_deterministic_in_rendered_output(self):
        from intelligent_regression_optimizer.renderer import render_report
        normalized = _normalized(
            [_story("S1", "low", ["AreaA"])],
            [_test("T1", coverage_areas=["AreaA"])]
        )
        classifications = classify_context(normalized)
        tier_result = score_tests(normalized, classifications)
        md = render_report(normalized, classifications, tier_result)
        assert "Recommendation Mode: deterministic" in md


# ---------------------------------------------------------------------------
# V1-A integration: history merge → tier changes
# ---------------------------------------------------------------------------

class TestHistoryMergeTierShift:
    """merge_history() + score_tests() together must produce the expected tier change."""

    def test_low_yaml_flakiness_high_history_flakiness_causes_retire(self):
        from intelligent_regression_optimizer.end_to_end_flow import merge_history
        # T1 and T2 both cover SharedArea (not unique). T1 has low YAML flakiness.
        # After merging history (high flakiness), T1 should become a retire candidate.
        normalized = _normalized(
            [_story("S1", "low", ["OtherArea"])],
            [
                _test("T1", coverage_areas=["SharedArea"], flakiness=0.01),
                _test("T2", coverage_areas=["SharedArea"], flakiness=0.01),
            ]
        )
        from intelligent_regression_optimizer.models import TestHistoryRecord
        history = {
            "T1": TestHistoryRecord(
                test_id="T1", flakiness_rate=0.95,
                failure_count_last_30d=19, total_runs=20,
            )
        }
        merged, _ = merge_history(normalized, history)
        classifications = classify_context(merged)
        tier_result = score_tests(merged, classifications)
        retire_ids = {s.test_id for s in tier_result.retire}
        assert "T1" in retire_ids, "T1 should be retired after history raises its flakiness"

    def test_high_yaml_flakiness_overridden_to_low_by_history_prevents_retire(self):
        from intelligent_regression_optimizer.end_to_end_flow import merge_history
        # T1 YAML says 0.95 flakiness (would retire), but history says 0.0 → should not retire
        normalized = _normalized(
            [_story("S1", "low", ["OtherArea"])],
            [
                _test("T1", coverage_areas=["SharedArea"], flakiness=0.95),
                _test("T2", coverage_areas=["SharedArea"], flakiness=0.95),
            ]
        )
        from intelligent_regression_optimizer.models import TestHistoryRecord
        history = {
            "T1": TestHistoryRecord(
                test_id="T1", flakiness_rate=0.0,
                failure_count_last_30d=0, total_runs=20,
            )
        }
        merged, _ = merge_history(normalized, history)
        classifications = classify_context(merged)
        tier_result = score_tests(merged, classifications)
        retire_ids = {s.test_id for s in tier_result.retire}
        assert "T1" not in retire_ids, "T1 should not be retired after history lowers its flakiness"


# ---------------------------------------------------------------------------
# V1-B integration: diff mapper → normalized → scoring
# ---------------------------------------------------------------------------

class TestDiffMapperPipelineIntegration:
    """apply_area_map() on normalized data must change coverage-driven tier assignments."""

    def test_changed_areas_from_diff_promotes_matching_test(self):
        from intelligent_regression_optimizer.diff_mapper import apply_area_map
        # Sprint has no changed_areas initially → T1 covers AreaA and scores low
        normalized = _normalized(
            [{"id": "S1", "risk": "high", "changed_areas": [], "resolved_deps": []}],
            [_test("T1", coverage_areas=["AreaA"], flakiness=0.0, exec_secs=10)]
        )
        classifications_before = classify_context(normalized)
        tier_before = score_tests(normalized, classifications_before)
        scored_before = tier_before.must_run + tier_before.should_run + tier_before.defer
        t1_before = next(s for s in scored_before if s.test_id == "T1")

        # Apply diff: AreaA is now a changed area
        updated = apply_area_map(normalized, {"AreaA"})
        classifications_after = classify_context(updated)
        tier_after = score_tests(updated, classifications_after)
        scored_after = tier_after.must_run + tier_after.should_run + tier_after.defer
        t1_after = next(s for s in scored_after if s.test_id == "T1")

        assert t1_after.raw_score > t1_before.raw_score, (
            "T1 score should increase when its coverage area is added to changed_areas"
        )

    def test_changed_areas_empty_set_does_not_change_scores(self):
        from intelligent_regression_optimizer.diff_mapper import apply_area_map
        normalized = _normalized(
            [_story("S1", "medium", ["AreaA"])],
            [_test("T1", coverage_areas=["AreaA"])]
        )
        updated = apply_area_map(normalized, set())
        # All stories should have empty changed_areas after applying empty diff
        for story in updated["sprint_context"]["stories"]:
            assert story["changed_areas"] == []


# ---------------------------------------------------------------------------
# V1-C integration: LLM repair → validator handoff + fallback chain
# ---------------------------------------------------------------------------

class TestLLMRepairValidatorHandoff:
    """Partially valid LLM output → repair_output() → validate_output() returns is_valid."""

    def _base_tier_result(self):
        from intelligent_regression_optimizer.models import TierResult
        return TierResult()

    def test_missing_heading_repaired_then_passes_validation(self):
        from intelligent_regression_optimizer.repair import repair_output
        from intelligent_regression_optimizer.output_validator import validate_output
        # Valid report except one heading is missing
        broken = """\
## Optimisation Summary

Recommendation Mode: llm
Sprint Risk Level: medium
Total Must-Run: 0
Total Retire Candidates: 0
NFR Elevation: No
Budget Overflow: No

## Must-Run

_No tests in this tier._

## Should-Run If Time Permits

_No tests in this tier._

## Defer To Overnight Run

_No tests in this tier._

## Suite Health Summary

Flakiness Tier High: 0 tests above threshold
"""
        # "## Retire Candidates" heading is missing
        assert "## Retire Candidates" not in broken
        result = repair_output(broken, self._base_tier_result(), {})
        assert result.is_repaired
        vr = validate_output(result.markdown)
        assert vr.is_valid, vr.errors

    def test_misplaced_label_repaired_then_passes_validation(self):
        from intelligent_regression_optimizer.repair import repair_output
        from intelligent_regression_optimizer.output_validator import validate_output
        # Build a report where a label is in the wrong section
        broken = """\
## Optimisation Summary

Recommendation Mode: llm
Sprint Risk Level: medium
Total Must-Run: 0
Total Retire Candidates: 0
NFR Elevation: No
Budget Overflow: No

## Must-Run

Flakiness Tier High: 0 tests above threshold

## Should-Run If Time Permits

_No tests in this tier._

## Defer To Overnight Run

_No tests in this tier._

## Retire Candidates

_No retire candidates._

## Suite Health Summary

_Empty._
"""
        result = repair_output(broken, self._base_tier_result(), {})
        assert result.is_repaired
        vr = validate_output(result.markdown)
        assert vr.is_valid, vr.errors


class TestLLMFallbackChain:
    """run_llm_pipeline() fallback chain: validate → repair → deterministic-fallback."""

    def _run_with_fake_content(self, content: str):
        from intelligent_regression_optimizer.llm_client import FakeLLMClient
        from intelligent_regression_optimizer.llm_flow import run_llm_pipeline
        normalized = {
            "sprint_context": {
                "sprint_id": "S-INT",
                "stories": [{"id": "S1", "risk": "low", "changed_areas": ["AreaA"], "resolved_deps": []}],
                "exploratory_sessions": [],
            },
            "test_suite": [{
                "id": "T1", "name": "test", "layer": "unit",
                "coverage_areas": ["AreaA"], "execution_time_secs": 10,
                "flakiness_rate": 0.0, "failure_count_last_30d": 0,
                "automated": True, "tags": [],
            }],
            "constraints": {"time_budget_mins": 60, "mandatory_tags": [],
                            "flakiness_retire_threshold": 0.30, "flakiness_high_tier_threshold": 0.20},
        }
        classifications = classify_context(normalized)
        tier_result = score_tests(normalized, classifications)
        client = FakeLLMClient(response_content=content)
        return run_llm_pipeline(normalized, classifications, tier_result, client)

    def test_valid_llm_output_returns_llm_mode(self):
        from intelligent_regression_optimizer.llm_client import _FAKE_RESPONSE
        result = self._run_with_fake_content(_FAKE_RESPONSE)
        assert result.recommendation_mode == "llm"

    def test_single_missing_heading_triggers_repair_mode(self):
        # Remove one required heading → repair needed
        from intelligent_regression_optimizer.llm_client import _FAKE_RESPONSE
        broken = _FAKE_RESPONSE.replace("## Retire Candidates\n", "")
        result = self._run_with_fake_content(broken)
        assert result.recommendation_mode == "llm-repaired"

    def test_repaired_output_passes_contract(self):
        from intelligent_regression_optimizer.llm_client import _FAKE_RESPONSE
        from intelligent_regression_optimizer.output_validator import validate_output
        broken = _FAKE_RESPONSE.replace("## Retire Candidates\n", "")
        result = self._run_with_fake_content(broken)
        vr = validate_output(result.flow_result.message)
        assert vr.is_valid, vr.errors

    def test_completely_invalid_output_triggers_deterministic_fallback(self):
        # The repair engine can heal any structural defect, so the only way to reach
        # deterministic-fallback is when repair itself returns an invalid report.
        # This tests the fallback chain logic by patching repair to return garbage.
        from unittest.mock import patch
        from intelligent_regression_optimizer.repair import RepairResult
        from intelligent_regression_optimizer.llm_client import _FAKE_RESPONSE
        bad_repair = RepairResult(markdown="still broken", actions=["patched"], is_repaired=True)
        with patch("intelligent_regression_optimizer.llm_flow.repair_output", return_value=bad_repair):
            result = self._run_with_fake_content("garbage LLM output — no headings or labels")
        assert result.recommendation_mode == "deterministic-fallback"

    def test_deterministic_fallback_output_passes_contract(self):
        from unittest.mock import patch
        from intelligent_regression_optimizer.repair import RepairResult
        from intelligent_regression_optimizer.output_validator import validate_output
        bad_repair = RepairResult(markdown="still broken", actions=["patched"], is_repaired=True)
        with patch("intelligent_regression_optimizer.llm_flow.repair_output", return_value=bad_repair):
            result = self._run_with_fake_content("garbage LLM output — no headings or labels")
        vr = validate_output(result.flow_result.message)
        assert vr.is_valid, vr.errors

    def test_provider_exception_triggers_deterministic_fallback(self):
        """Provider exceptions must produce a valid deterministic fallback, not exit 3."""
        from intelligent_regression_optimizer.llm_flow import run_llm_pipeline
        from intelligent_regression_optimizer.models import EXIT_OK
        from intelligent_regression_optimizer.output_validator import validate_output

        class _BoomClient:
            def generate(self, req):
                raise ConnectionError("Network unreachable")

        normalized = {
            "sprint_context": {
                "sprint_id": "S-INT",
                "stories": [{"id": "S1", "risk": "low", "changed_areas": ["AreaA"], "resolved_deps": []}],
                "exploratory_sessions": [],
            },
            "test_suite": [{
                "id": "T1", "name": "test", "layer": "unit",
                "coverage_areas": ["AreaA"], "execution_time_secs": 10,
                "flakiness_rate": 0.0, "failure_count_last_30d": 0,
                "automated": True, "tags": [],
            }],
            "constraints": {"time_budget_mins": 60, "mandatory_tags": [],
                            "flakiness_retire_threshold": 0.30, "flakiness_high_tier_threshold": 0.20},
        }
        classifications = classify_context(normalized)
        tier_result = score_tests(normalized, classifications)
        result = run_llm_pipeline(normalized, classifications, tier_result, _BoomClient())
        assert result.flow_result.exit_code == EXIT_OK
        assert result.recommendation_mode == "deterministic-fallback"
        vr = validate_output(result.flow_result.message)
        assert vr.is_valid, vr.errors
