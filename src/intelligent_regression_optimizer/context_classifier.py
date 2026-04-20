"""Context classifier for intelligent-regression-optimizer.

Derives sprint-level and per-test dimensions from the normalised input package.
All outputs are plain dicts to keep the classifier a pure function.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Suite health thresholds
# ---------------------------------------------------------------------------
_DEGRADED_FLAKY_PCT = 0.20   # >20% of suite above flakiness_high_tier_threshold → degraded
_STABLE_FLAKY_PCT   = 0.05   # <5% → stable; otherwise moderate

# Time pressure multiples of budget
_TIGHT_MULTIPLE    = 3.0
_MODERATE_MULTIPLE = 1.5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_context(normalized: dict[str, Any]) -> dict[str, Any]:
    """Derive classification dimensions from the normalised input document.

    Args:
        normalized: The ``normalized`` dict from :class:`InputPackage`.

    Returns:
        A flat dict with the following keys:

        - ``sprint_risk_level``   : ``"high"`` | ``"medium"`` | ``"low"``
        - ``nfr_elevation_required``: ``bool``
        - ``suite_health``        : ``"degraded"`` | ``"moderate"`` | ``"stable"``
        - ``time_pressure``       : ``"tight"`` | ``"moderate"`` | ``"relaxed"``
        - ``per_test_stability``  : ``dict[test_id, float]``  (0.0 – 1.0)
    """
    sprint = normalized["sprint_context"]
    stories: list[dict] = sprint.get("stories", [])
    tests: list[dict] = normalized.get("test_suite", [])
    constraints: dict = normalized.get("constraints", {})

    sprint_risk = _derive_sprint_risk(stories)
    nfr_elevation = sprint_risk == "high"
    suite_health = _derive_suite_health(tests, constraints)
    time_pressure = _derive_time_pressure(tests, constraints)
    stability_scores = _derive_per_test_stability(tests)

    return {
        "sprint_risk_level": sprint_risk,
        "nfr_elevation_required": nfr_elevation,
        "suite_health": suite_health,
        "time_pressure": time_pressure,
        "per_test_stability": stability_scores,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _derive_sprint_risk(stories: list[dict]) -> str:
    risk_values = {s["risk"] for s in stories}
    if "high" in risk_values:
        return "high"
    if "medium" in risk_values:
        return "medium"
    return "low"


def _derive_suite_health(tests: list[dict], constraints: dict) -> str:
    if not tests:
        return "stable"
    threshold = constraints.get("flakiness_high_tier_threshold", 0.20)
    above = sum(1 for t in tests if t.get("flakiness_rate", 0) > threshold)
    ratio = above / len(tests)
    if ratio > _DEGRADED_FLAKY_PCT:
        return "degraded"
    if ratio < _STABLE_FLAKY_PCT:
        return "stable"
    return "moderate"


def _derive_time_pressure(tests: list[dict], constraints: dict) -> str:
    budget_secs = constraints.get("time_budget_mins", 30) * 60
    if budget_secs == 0:
        return "tight"
    total_secs = sum(t.get("execution_time_secs", 0) for t in tests)
    multiple = total_secs / budget_secs
    if multiple > _TIGHT_MULTIPLE:
        return "tight"
    if multiple > _MODERATE_MULTIPLE:
        return "moderate"
    return "relaxed"


def _derive_per_test_stability(tests: list[dict]) -> dict[str, float]:
    """Compute stability_score for each test.

    Formula: ``1.0 - (0.7 × flakiness_rate + 0.3 × min(failure_count_last_30d / 10, 1.0))``
    Clamped to [0.0, 1.0].
    """
    scores: dict[str, float] = {}
    for test in tests:
        flakiness = test.get("flakiness_rate", 0.0)
        failures = test.get("failure_count_last_30d", 0)
        failure_component = min(failures / 10.0, 1.0)
        score = 1.0 - (0.7 * flakiness + 0.3 * failure_component)
        scores[test["id"]] = max(0.0, score)
    return scores
