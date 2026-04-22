"""Tests for prompt builder with scenario routing."""
from __future__ import annotations

import pytest

from intelligent_regression_optimizer.models import ScoredTest, TierResult
from intelligent_regression_optimizer.prompt_builder import build_prompt


def _make_tier_result(**kwargs) -> TierResult:
    defaults = dict(must_run=[], should_run=[], defer=[], retire=[], budget_overflow=False)
    defaults.update(kwargs)
    return TierResult(**defaults)


def _make_scored_test(test_id: str = "T-01", tier: str = "must-run") -> ScoredTest:
    return ScoredTest(
        test_id=test_id, name="Some test", raw_score=8.0, tier=tier,
        is_override=False, override_reason=None, is_manual=False, flakiness_rate=0.0,
    )


def _base_normalized() -> dict:
    return {
        "sprint_context": {
            "sprint_name": "Sprint 42",
            "stories": [{"id": "S-1", "risk": "medium", "changed_areas": ["api"]}],
        },
        "test_suite": [
            {"id": "T-01", "name": "Login test", "execution_time_secs": 120},
        ],
        "constraints": {
            "time_budget_mins": 60,
            "flakiness_high_tier_threshold": 0.20,
        },
    }


def _base_classifications(
    sprint_risk_level: str = "medium",
    suite_health: str = "stable",
    time_pressure: str = "moderate",
    nfr_elevation_required: bool = False,
) -> dict:
    return {
        "sprint_risk_level": sprint_risk_level,
        "suite_health": suite_health,
        "time_pressure": time_pressure,
        "nfr_elevation_required": nfr_elevation_required,
        "per_test_stability": {},
    }


# ---------------------------------------------------------------------------
# Return value shape
# ---------------------------------------------------------------------------

def test_build_prompt_returns_tuple():
    result = build_prompt(_base_normalized(), _base_classifications(), _make_tier_result())
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_build_prompt_both_strings():
    sys_p, usr_p = build_prompt(_base_normalized(), _base_classifications(), _make_tier_result())
    assert isinstance(sys_p, str) and len(sys_p) > 0
    assert isinstance(usr_p, str) and len(usr_p) > 0


# ---------------------------------------------------------------------------
# Scenario routing
# ---------------------------------------------------------------------------

def test_high_risk_routes_to_high_risk_template():
    classifications = _base_classifications(sprint_risk_level="high")
    _, usr_p = build_prompt(_base_normalized(), classifications, _make_tier_result())
    assert "HIGH risk" in usr_p


def test_degraded_suite_routes_to_degraded_template():
    classifications = _base_classifications(suite_health="degraded")
    _, usr_p = build_prompt(_base_normalized(), classifications, _make_tier_result())
    assert "DEGRADED" in usr_p


def test_budget_pressure_routes_correctly():
    classifications = _base_classifications(time_pressure="tight")
    tier = _make_tier_result(budget_overflow=True)
    _, usr_p = build_prompt(_base_normalized(), classifications, tier)
    assert "time-pressured" in usr_p.lower() or "budget" in usr_p.lower()


def test_balanced_is_default():
    classifications = _base_classifications()
    _, usr_p = build_prompt(_base_normalized(), classifications, _make_tier_result())
    assert "balanced" in usr_p.lower() or "Produce a balanced" in usr_p


def test_high_risk_takes_priority_over_degraded():
    classifications = _base_classifications(sprint_risk_level="high", suite_health="degraded")
    _, usr_p = build_prompt(_base_normalized(), classifications, _make_tier_result())
    assert "HIGH risk" in usr_p


# ---------------------------------------------------------------------------
# Field inclusion (insight #5: no silent field omission)
# ---------------------------------------------------------------------------

def test_user_prompt_contains_sprint_risk_level():
    classifications = _base_classifications(sprint_risk_level="medium")
    _, usr_p = build_prompt(_base_normalized(), classifications, _make_tier_result())
    assert "medium" in usr_p


def test_user_prompt_contains_time_budget():
    _, usr_p = build_prompt(_base_normalized(), _base_classifications(), _make_tier_result())
    assert "60" in usr_p


def test_user_prompt_contains_tier_assignments():
    tier = _make_tier_result(must_run=[_make_scored_test("T-01", "must-run")])
    _, usr_p = build_prompt(_base_normalized(), _base_classifications(), tier)
    assert "T-01" in usr_p


def test_user_prompt_contains_nfr_elevation():
    classifications = _base_classifications(nfr_elevation_required=True)
    _, usr_p = build_prompt(_base_normalized(), classifications, _make_tier_result())
    assert "True" in usr_p or "nfr" in usr_p.lower()


def test_user_prompt_contains_budget_overflow():
    tier = _make_tier_result(budget_overflow=True)
    _, usr_p = build_prompt(_base_normalized(), _base_classifications(), tier)
    assert "True" in usr_p or "overflow" in usr_p.lower()


def test_system_prompt_contains_output_contract():
    sys_p, _ = build_prompt(_base_normalized(), _base_classifications(), _make_tier_result())
    assert "## Optimisation Summary" in sys_p
    assert "Recommendation Mode:" in sys_p


def test_user_prompt_contains_all_tier_types():
    retire_test = ScoredTest(
        test_id="T-04", name="Old test", raw_score=1.0, tier="retire",
        is_override=False, override_reason=None, is_manual=False, flakiness_rate=0.35,
    )
    tier = _make_tier_result(
        must_run=[_make_scored_test("T-01", "must-run")],
        should_run=[_make_scored_test("T-02", "should-run")],
        defer=[_make_scored_test("T-03", "defer")],
        retire=[retire_test],
    )
    _, usr_p = build_prompt(_base_normalized(), _base_classifications(), tier)
    assert "T-01" in usr_p
    assert "T-02" in usr_p
    assert "T-03" in usr_p
    assert "T-04" in usr_p


# ---------------------------------------------------------------------------
# R3: Override reason + history provenance (F3)
# ---------------------------------------------------------------------------

def test_override_reason_included_in_tier_assignments():
    """When a test is overridden, the override reason must appear in the user prompt."""
    overridden = ScoredTest(
        test_id="T-OV", name="Override me", raw_score=6.0, tier="must-run",
        is_override=True, override_reason="mandatory: regulatory audit",
        is_manual=False, flakiness_rate=0.0,
    )
    tier = _make_tier_result(must_run=[overridden])
    _, usr_p = build_prompt(_base_normalized(), _base_classifications(), tier)
    assert "regulatory audit" in usr_p


def test_no_override_noise_for_normal_tests():
    """Non-overridden tests must not have an override note in the prompt."""
    tier = _make_tier_result(must_run=[_make_scored_test("T-01")])
    _, usr_p = build_prompt(_base_normalized(), _base_classifications(), tier)
    assert "override" not in usr_p.lower()


def test_history_source_ci_in_user_prompt():
    """When flakiness data comes from CI history, that provenance is stated in the prompt."""
    normalized = _base_normalized()
    normalized.setdefault("_meta", {})["history_source"] = "ci-history"
    _, usr_p = build_prompt(normalized, _base_classifications(), _make_tier_result())
    assert "ci-history" in usr_p.lower() or "ci history" in usr_p.lower()


def test_history_source_defaults_to_input_yaml_when_absent():
    """When no _meta key is present the prompt states data comes from input YAML."""
    normalized = _base_normalized()  # no _meta key
    _, usr_p = build_prompt(normalized, _base_classifications(), _make_tier_result())
    assert "input" in usr_p.lower() or "yaml" in usr_p.lower()
