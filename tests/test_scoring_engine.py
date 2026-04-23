"""Unit tests for scoring_engine.py — written RED before implementation.

Scoring formula (locked):
  raw = (10 × direct_coverage × risk_mult)
      + (5  × dep_coverage   × dep_risk_mult)
      + (3  × exploratory_match)
      - (8  × flakiness_rate)

  risk_mult:     high=1.0, medium=0.6, low=0.3
  dep_risk_mult: same scale × 0.5 discount
  direct/dep_coverage: 1 if any coverage_area ∩ changed_areas, else 0
  exploratory_match:   1 if any coverage_area ∈ session.risk_areas, else 0

Tiers: must-run ≥ 8, should-run ≥ 4, defer < 4.
Hard overrides (mandatory tag, NFR elevation) bypass scoring — always must-run.
"""
import pytest
from intelligent_regression_optimizer.scoring_engine import score_tests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FLAKINESS_RETIRE_THRESHOLD = 0.30
FLAKINESS_HIGH_THRESHOLD = 0.20


def _normalized(stories, tests, budget_mins=60, mandatory_tags=None, exploratory=None):
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
            "mandatory_tags": mandatory_tags or [],
            "flakiness_retire_threshold": FLAKINESS_RETIRE_THRESHOLD,
            "flakiness_high_tier_threshold": FLAKINESS_HIGH_THRESHOLD,
        },
    }


def _classifications(sprint_risk="low", nfr_elevation=False):
    return {
        "sprint_risk_level": sprint_risk,
        "nfr_elevation_required": nfr_elevation,
        "suite_health": "stable",
        "time_pressure": "relaxed",
        "per_test_stability": {},
    }


def _story(id_, risk, changed_areas, deps=None):
    return {
        "id": id_,
        "risk": risk,
        "changed_areas": changed_areas,
        "resolved_deps": deps or [],
    }


def _test(id_, coverage_areas, layer="unit", flakiness=0.0, exec_secs=60,
          automated=True, tags=None, failures=0):
    return {
        "id": id_,
        "name": f"test {id_}",
        "layer": layer,
        "coverage_areas": coverage_areas,
        "execution_time_secs": exec_secs,
        "flakiness_rate": flakiness,
        "failure_count_last_30d": failures,
        "automated": automated,
        "tags": tags or [],
    }


def _dep_story(id_, risk, changed_areas):
    return {"id": id_, "risk": risk, "changed_areas": changed_areas}


# ---------------------------------------------------------------------------
# Raw score formula — direct coverage
# ---------------------------------------------------------------------------

class TestDirectCoverageScoring:
    def test_direct_coverage_high_risk_scores_10(self):
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"])]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        t1 = next(s for s in result.must_run + result.should_run + result.defer if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(10.0)

    def test_direct_coverage_medium_risk_scores_6(self):
        stories = [_story("S1", "medium", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"])]
        result = score_tests(_normalized(stories, tests), _classifications("medium"))
        t1 = next(s for s in result.must_run + result.should_run + result.defer if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(6.0)

    def test_direct_coverage_low_risk_scores_3(self):
        stories = [_story("S1", "low", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"])]
        result = score_tests(_normalized(stories, tests), _classifications("low"))
        t1 = next(s for s in result.must_run + result.should_run + result.defer if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(3.0)

    def test_no_coverage_match_scores_zero_base(self):
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [_test("T1", ["ServiceB"])]  # no overlap
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        all_scored = result.must_run + result.should_run + result.defer + result.retire
        t1 = next(s for s in all_scored if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(0.0)

    def test_multiple_stories_uses_highest_risk(self):
        stories = [
            _story("S1", "low", ["ServiceA"]),
            _story("S2", "high", ["ServiceA"]),
        ]
        tests = [_test("T1", ["ServiceA"])]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        all_scored = result.must_run + result.should_run + result.defer
        t1 = next(s for s in all_scored if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(10.0)  # uses high, not low


# ---------------------------------------------------------------------------
# Dependency coverage
# ---------------------------------------------------------------------------

class TestDepCoverageScoring:
    def test_dep_coverage_high_risk_scores_2_5(self):
        # dep story risk=high: 5 × 1 × (1.0 × 0.5) = 2.5
        dep = _dep_story("D1", "high", ["DepService"])
        stories = [_story("S1", "low", ["OtherService"], deps=[dep])]
        tests = [_test("T1", ["DepService"])]  # only matches dep, not direct
        result = score_tests(_normalized(stories, tests), _classifications("low"))
        all_scored = result.must_run + result.should_run + result.defer
        t1 = next(s for s in all_scored if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(2.5)

    def test_dep_coverage_medium_risk_scores_1_5(self):
        # dep story risk=medium: 5 × 1 × (0.6 × 0.5) = 1.5
        dep = _dep_story("D1", "medium", ["DepService"])
        stories = [_story("S1", "low", ["OtherService"], deps=[dep])]
        tests = [_test("T1", ["DepService"])]
        result = score_tests(_normalized(stories, tests), _classifications("low"))
        all_scored = result.must_run + result.should_run + result.defer
        t1 = next(s for s in all_scored if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(1.5)

    def test_direct_plus_dep_coverage_combines(self):
        # direct high=10, dep high=2.5 → 12.5
        dep = _dep_story("D1", "high", ["DepService"])
        stories = [_story("S1", "high", ["MainService"], deps=[dep])]
        tests = [_test("T1", ["MainService", "DepService"])]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        all_scored = result.must_run + result.should_run + result.defer
        t1 = next(s for s in all_scored if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(12.5)


# ---------------------------------------------------------------------------
# Exploratory match
# ---------------------------------------------------------------------------

class TestExploratoryScoring:
    def test_exploratory_match_adds_3(self):
        stories = [_story("S1", "low", ["OtherArea"])]
        exploratory = [{"session_id": "EX1", "risk_areas": ["ServiceA"], "tester": "alice", "notes": ""}]
        tests = [_test("T1", ["ServiceA"])]
        result = score_tests(
            _normalized(stories, tests, exploratory=exploratory),
            _classifications("low")
        )
        all_scored = result.must_run + result.should_run + result.defer
        t1 = next(s for s in all_scored if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(3.0)  # 0 direct + 3 exploratory

    def test_no_exploratory_match_adds_zero(self):
        stories = [_story("S1", "low", ["OtherArea"])]
        exploratory = [{"session_id": "EX1", "risk_areas": ["UnrelatedArea"], "tester": "alice", "notes": ""}]
        tests = [_test("T1", ["ServiceA"])]
        result = score_tests(
            _normalized(stories, tests, exploratory=exploratory),
            _classifications("low")
        )
        all_scored = result.must_run + result.should_run + result.defer
        t1 = next(s for s in all_scored if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Flakiness penalty
# ---------------------------------------------------------------------------

class TestFlakinessScoring:
    def test_flakiness_penalty_reduces_score(self):
        # direct high=10, flakiness 0.25: 10 - 8×0.25 = 10 - 2 = 8.0
        # T2 added to remove unique coverage so T1 stays in scored tiers
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"], flakiness=0.25), _test("T2", ["ServiceA"], flakiness=0.0)]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        all_scored = result.must_run + result.should_run + result.defer
        t1 = next(s for s in all_scored if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(8.0)

    def test_high_flakiness_can_push_score_negative(self):
        # no coverage, flakiness 1.0: 0 - 8 = -8 → defer
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [_test("T1", ["ServiceB"], flakiness=1.0)]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        all_scored = result.must_run + result.should_run + result.defer + result.retire
        t1 = next(s for s in all_scored if s.test_id == "T1")
        assert t1.raw_score == pytest.approx(-8.0)


# ---------------------------------------------------------------------------
# Hard overrides — mandatory tags
# ---------------------------------------------------------------------------

class TestMandatoryTagOverride:
    def test_mandatory_tag_always_must_run(self):
        stories = [_story("S1", "low", ["OtherArea"])]
        tests = [_test("T1", ["UnrelatedArea"], tags=["critical-flow"])]
        result = score_tests(
            _normalized(stories, tests, mandatory_tags=["critical-flow"]),
            _classifications("low")
        )
        ids = [s.test_id for s in result.must_run]
        assert "T1" in ids

    def test_mandatory_tag_override_sets_is_override_true(self):
        stories = [_story("S1", "low", ["OtherArea"])]
        tests = [_test("T1", ["UnrelatedArea"], tags=["critical-flow"])]
        result = score_tests(
            _normalized(stories, tests, mandatory_tags=["critical-flow"]),
            _classifications("low")
        )
        t1 = next(s for s in result.must_run if s.test_id == "T1")
        assert t1.is_override is True

    def test_mandatory_tag_overrides_low_raw_score(self):
        # Score would be 0 without override
        stories = [_story("S1", "low", ["OtherArea"])]
        tests = [_test("T1", ["UnrelatedArea"], flakiness=1.0, tags=["critical-flow"])]
        result = score_tests(
            _normalized(stories, tests, mandatory_tags=["critical-flow"]),
            _classifications("low")
        )
        assert any(s.test_id == "T1" for s in result.must_run)


# ---------------------------------------------------------------------------
# Hard overrides — NFR elevation
# ---------------------------------------------------------------------------

class TestNfrElevationOverride:
    def test_nfr_elevation_performance_layer_must_run(self):
        stories = [_story("S1", "high", ["OtherArea"])]
        tests = [_test("T1", ["UnrelatedArea"], layer="performance")]
        result = score_tests(
            _normalized(stories, tests),
            _classifications("high", nfr_elevation=True)
        )
        assert any(s.test_id == "T1" for s in result.must_run)

    def test_nfr_elevation_security_layer_must_run(self):
        stories = [_story("S1", "high", ["OtherArea"])]
        tests = [_test("T1", ["UnrelatedArea"], layer="security")]
        result = score_tests(
            _normalized(stories, tests),
            _classifications("high", nfr_elevation=True)
        )
        assert any(s.test_id == "T1" for s in result.must_run)

    def test_nfr_elevation_does_not_affect_functional_layer(self):
        stories = [_story("S1", "high", ["OtherArea"])]
        tests = [_test("T1", ["UnrelatedArea"], layer="unit")]
        result = score_tests(
            _normalized(stories, tests),
            _classifications("high", nfr_elevation=True)
        )
        # Should be in defer (score=0, no override), not must-run
        assert not any(s.test_id == "T1" for s in result.must_run)
        assert any(s.test_id == "T1" for s in result.defer)


# ---------------------------------------------------------------------------
# Tier thresholds
# ---------------------------------------------------------------------------

class TestTierThresholds:
    def test_score_above_8_is_must_run(self):
        # high risk direct = 10.0 → must-run
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"])]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        assert any(s.test_id == "T1" for s in result.must_run)

    def test_score_exactly_8_is_must_run(self):
        # high risk (10) - flakiness 0.25 (−2) = 8.0 → must-run (≥8)
        # T2 added to remove unique coverage so T1 stays in scored tiers
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"], flakiness=0.25), _test("T2", ["ServiceA"], flakiness=0.0)]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        assert any(s.test_id == "T1" for s in result.must_run)

    def test_score_between_4_and_8_is_should_run(self):
        # medium risk direct = 6.0 → should-run
        stories = [_story("S1", "medium", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"])]
        result = score_tests(_normalized(stories, tests), _classifications("medium"))
        assert any(s.test_id == "T1" for s in result.should_run)

    def test_score_exactly_4_is_should_run(self):
        # medium risk (6) - flakiness 0.25 (−2) = 4.0 → should-run (≥4)
        # T2 added to remove unique coverage so T1 stays in scored tiers
        stories = [_story("S1", "medium", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"], flakiness=0.25), _test("T2", ["ServiceA"], flakiness=0.0)]
        result = score_tests(_normalized(stories, tests), _classifications("medium"))
        assert any(s.test_id == "T1" for s in result.should_run)

    def test_score_below_4_is_defer(self):
        # low risk direct = 3.0 → defer
        stories = [_story("S1", "low", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"])]
        result = score_tests(_normalized(stories, tests), _classifications("low"))
        assert any(s.test_id == "T1" for s in result.defer)


# ---------------------------------------------------------------------------
# Retire candidates
# ---------------------------------------------------------------------------

class TestRetireCandidates:
    def test_retire_flaky_no_unique_coverage_automated(self):
        # Two tests both covering ServiceA → neither has unique coverage
        # T1 is above retire threshold (0.35 > 0.30)
        stories = [_story("S1", "low", ["OtherArea"])]
        tests = [
            _test("T1", ["ServiceA"], flakiness=0.35, automated=True),
            _test("T2", ["ServiceA"], flakiness=0.01, automated=True),
        ]
        result = score_tests(_normalized(stories, tests), _classifications("low"))
        assert any(s.test_id == "T1" for s in result.retire)

    def test_retire_excluded_when_has_unique_coverage(self):
        # T1 covers UniqueArea not covered by any other test → has unique coverage → not retired
        stories = [_story("S1", "low", ["OtherArea"])]
        tests = [
            _test("T1", ["UniqueArea"], flakiness=0.35, automated=True),
            _test("T2", ["SharedArea"], flakiness=0.01, automated=True),
        ]
        result = score_tests(_normalized(stories, tests), _classifications("low"))
        assert not any(s.test_id == "T1" for s in result.retire)

    def test_retire_excluded_for_manual_test(self):
        # Manual tests never retired even if flaky and non-unique
        stories = [_story("S1", "low", ["OtherArea"])]
        tests = [
            _test("T1", ["ServiceA"], flakiness=0.35, automated=False),
            _test("T2", ["ServiceA"], flakiness=0.01, automated=True),
        ]
        result = score_tests(_normalized(stories, tests), _classifications("low"))
        assert not any(s.test_id == "T1" for s in result.retire)

    def test_retire_requires_both_flaky_and_non_unique(self):
        # T1: flaky but has unique coverage → NOT retired
        # T2: non-unique but not flaky → NOT retired
        stories = [_story("S1", "low", ["OtherArea"])]
        tests = [
            _test("T1", ["UniqueArea", "SharedArea"], flakiness=0.35, automated=True),
            _test("T2", ["SharedArea"], flakiness=0.01, automated=True),
        ]
        result = score_tests(_normalized(stories, tests), _classifications("low"))
        assert not any(s.test_id in ("T1", "T2") for s in result.retire)


# ---------------------------------------------------------------------------
# Budget overflow
# ---------------------------------------------------------------------------

class TestBudgetOverflow:
    def test_budget_overflow_sets_flag(self):
        # 3 tests × 25 min each = 75 min > 60 min budget
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [_test(f"T{i}", ["ServiceA"], exec_secs=1500) for i in range(1, 4)]
        result = score_tests(_normalized(stories, tests, budget_mins=60), _classifications("high"))
        assert result.budget_overflow is True

    def test_budget_overflow_demotes_lowest_scored_to_should_run(self):
        # T1 score=10 (high direct), T2 score=8 (high direct, flakiness 0.25)
        # budget only fits one → T2 (lowest score=8) demoted
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [
            _test("T1", ["ServiceA"], exec_secs=2400),   # 40 min
            _test("T2", ["ServiceA"], flakiness=0.25, exec_secs=2400),  # 40 min, score=8
        ]
        result = score_tests(_normalized(stories, tests, budget_mins=60), _classifications("high"))
        assert result.budget_overflow is True
        # T2 (lower score) should be demoted to should-run
        assert any(s.test_id == "T2" for s in result.should_run)
        # T1 (higher score) stays must-run
        assert any(s.test_id == "T1" for s in result.must_run)

    def test_budget_hard_overrides_exempt_from_budget(self):
        # mandatory tag test is exempt — stays must-run even if budget exceeded
        stories = [_story("S1", "high", ["OtherArea"])]
        tests = [
            _test("T1", ["UnrelatedArea"], tags=["critical-flow"], exec_secs=7200),  # 120 min
        ]
        result = score_tests(
            _normalized(stories, tests, budget_mins=60, mandatory_tags=["critical-flow"]),
            _classifications("high")
        )
        assert any(s.test_id == "T1" for s in result.must_run)

    def test_no_overflow_when_within_budget(self):
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"], exec_secs=600)]  # 10 min, budget 60 min
        result = score_tests(_normalized(stories, tests, budget_mins=60), _classifications("high"))
        assert result.budget_overflow is False


# ---------------------------------------------------------------------------
# Manual test handling
# ---------------------------------------------------------------------------

class TestManualTests:
    def test_manual_test_excluded_from_budget_calc(self):
        # Manual test is huge (200 min) but should not consume the budget
        # T1 = manual 200 min (excluded from budget)
        # T2 = automated 10 min (fits in 15 min budget)
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [
            _test("T1", ["ServiceA"], exec_secs=12000, automated=False),
            _test("T2", ["ServiceA"], exec_secs=600, automated=True),
        ]
        result = score_tests(_normalized(stories, tests, budget_mins=15), _classifications("high"))
        assert result.budget_overflow is False

    def test_manual_test_is_tiered(self):
        # Manual test should appear in a tier (not be dropped)
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"], automated=False)]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        all_tiered = result.must_run + result.should_run + result.defer
        assert any(s.test_id == "T1" for s in all_tiered)

    def test_manual_test_tagged_is_manual(self):
        stories = [_story("S1", "high", ["ServiceA"])]
        tests = [_test("T1", ["ServiceA"], automated=False)]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        all_tiered = result.must_run + result.should_run + result.defer
        t1 = next(s for s in all_tiered if s.test_id == "T1")
        assert t1.is_manual is True


# ---------------------------------------------------------------------------
# F1.2 RED — flaky-critical detection decision table
# ---------------------------------------------------------------------------

class TestFlakyCriticalDetection:
    """Tests covering every row of the flaky-critical decision table.

    Qualifying conditions (all must be true):
    1. flakiness_rate > flakiness_high_tier_threshold (0.20)
    2. direct coverage overlap with a sprint story's changed_areas
    3. matched story has risk: medium or high
    4. test has unique coverage (at least one coverage_area covered by no other test)
    """

    def test_flaky_impacted_unique_high_risk_is_flaky_critical(self):
        # All 4 conditions met — high risk story
        stories = [_story("S1", "high", ["Checkout"])]
        tests = [_test("T1", ["Checkout"], flakiness=0.35)]  # unique; flaky; high-risk impacted
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        assert any(s.test_id == "T1" for s in result.flaky_critical)
        # Must NOT appear in any scored tier
        all_scored = result.must_run + result.should_run + result.defer + result.retire
        assert not any(s.test_id == "T1" for s in all_scored)

    def test_flaky_impacted_unique_medium_risk_is_flaky_critical(self):
        # All 4 conditions met — medium risk story
        stories = [_story("S1", "medium", ["AuthService"])]
        tests = [_test("T1", ["AuthService"], flakiness=0.25)]
        result = score_tests(_normalized(stories, tests), _classifications("medium"))
        assert any(s.test_id == "T1" for s in result.flaky_critical)
        all_scored = result.must_run + result.should_run + result.defer + result.retire
        assert not any(s.test_id == "T1" for s in all_scored)

    def test_flaky_impacted_unique_low_risk_is_normal_tier(self):
        # Condition 3 fails — low risk story does NOT qualify
        stories = [_story("S1", "low", ["ReportService"])]
        tests = [_test("T1", ["ReportService"], flakiness=0.30)]
        result = score_tests(_normalized(stories, tests), _classifications("low"))
        assert not any(s.test_id == "T1" for s in result.flaky_critical)
        all_scored = result.must_run + result.should_run + result.defer + result.retire
        assert any(s.test_id == "T1" for s in all_scored)

    def test_flaky_impacted_no_unique_coverage_is_retire(self):
        # Condition 4 fails — no unique coverage → falls to retire (above retire threshold)
        stories = [_story("S1", "high", ["Checkout"])]
        tests = [
            _test("T1", ["Checkout"], flakiness=0.35),  # flaky; no unique (T2 also covers Checkout)
            _test("T2", ["Checkout"], flakiness=0.01),
        ]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        assert not any(s.test_id == "T1" for s in result.flaky_critical)
        assert any(s.test_id == "T1" for s in result.retire)

    def test_flaky_not_impacted_is_normal_tier(self):
        # Condition 2 fails — test doesn't overlap sprint story's changed_areas
        stories = [_story("S1", "high", ["PaymentService"])]
        tests = [_test("T1", ["ReportingModule"], flakiness=0.30)]  # unique but not impacted
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        assert not any(s.test_id == "T1" for s in result.flaky_critical)

    def test_low_flakiness_impacted_unique_is_normal_tier(self):
        # Condition 1 fails — flakiness below threshold (0.20)
        stories = [_story("S1", "high", ["Checkout"])]
        tests = [_test("T1", ["Checkout"], flakiness=0.15)]  # reliable enough
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        assert not any(s.test_id == "T1" for s in result.flaky_critical)
        # Should be Must-Run (high-risk, low flakiness)
        assert any(s.test_id == "T1" for s in result.must_run)

    def test_flaky_critical_is_budget_exempt(self):
        # Flaky-critical tests must NOT consume budget or be demoted under overflow
        stories = [_story("S1", "high", ["Checkout"])]
        tests = [
            _test("T1", ["Checkout"], flakiness=0.35, exec_secs=7200),  # 120 min > budget
        ]
        result = score_tests(_normalized(stories, tests, budget_mins=60), _classifications("high"))
        # T1 is flaky-critical; budget overflow must NOT affect it
        assert any(s.test_id == "T1" for s in result.flaky_critical)

    def test_flaky_critical_not_in_must_run_or_should_run(self):
        # Flaky-critical tests should never also appear in Must-Run/Should-Run/Defer/Retire
        stories = [_story("S1", "high", ["Checkout"])]
        tests = [_test("T1", ["Checkout"], flakiness=0.35)]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        all_tiers = result.must_run + result.should_run + result.defer + result.retire
        assert not any(s.test_id == "T1" for s in all_tiers)
        assert any(s.test_id == "T1" for s in result.flaky_critical)

    def test_flaky_critical_test_has_is_flaky_critical_true(self):
        # Scored test in flaky_critical list must carry is_flaky_critical=True
        stories = [_story("S1", "high", ["Checkout"])]
        tests = [_test("T1", ["Checkout"], flakiness=0.35)]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        fc_test = next(s for s in result.flaky_critical if s.test_id == "T1")
        assert fc_test.is_flaky_critical is True

    def test_flaky_critical_reason_contains_unique_area(self):
        # Reason string should name the unique coverage area(s)
        stories = [_story("S1", "high", ["Checkout"])]
        tests = [_test("T1", ["Checkout"], flakiness=0.35)]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        fc_test = next(s for s in result.flaky_critical if s.test_id == "T1")
        assert fc_test.flaky_critical_reason is not None
        assert "Checkout" in fc_test.flaky_critical_reason

    def test_normal_tests_coexist_with_flaky_critical(self):
        # A clean high-risk test alongside a flaky-critical test
        stories = [_story("S1", "high", ["Checkout"]), _story("S2", "high", ["PaymentService"])]
        tests = [
            _test("T1", ["Checkout"], flakiness=0.35),     # unique; flaky → flaky-critical
            _test("T2", ["PaymentService"], flakiness=0.0), # clean → must-run
        ]
        result = score_tests(_normalized(stories, tests), _classifications("high"))
        assert any(s.test_id == "T1" for s in result.flaky_critical)
        assert any(s.test_id == "T2" for s in result.must_run)

    def test_mandatory_tagged_flaky_critical_is_must_run_override(self):
        # A test qualifies as flaky-critical (all 4 conditions) AND has a mandatory tag.
        # Override (mandatory tag) must win — test lands in must_run, not flaky_critical.
        stories = [_story("S1", "high", ["Checkout"])]
        tests = [_test("T1", ["Checkout"], flakiness=0.35, tags=["smoke"])]
        result = score_tests(
            _normalized(stories, tests, mandatory_tags=["smoke"]),
            _classifications("high"),
        )
        # Override wins: T1 must be in must_run with is_override=True
        assert any(s.test_id == "T1" for s in result.must_run)
        t1 = next(s for s in result.must_run if s.test_id == "T1")
        assert t1.is_override is True
        # Must NOT appear in flaky_critical
        assert not any(s.test_id == "T1" for s in result.flaky_critical)
