"""Markdown report renderer for intelligent-regression-optimizer."""
from __future__ import annotations

from typing import Any

from intelligent_regression_optimizer.models import ScoredTest, TierResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_test(st: ScoredTest) -> str:
    """Format a single scored test as a list item."""
    manual_tag = " (manual)" if st.is_manual else ""
    override_note = f" [override: {st.override_reason}]" if st.is_override and st.override_reason else ""
    return f"- {st.test_id} {st.name} (score: {st.raw_score:.1f}){override_note}{manual_tag}"


def _fmt_retire(st: ScoredTest) -> str:
    return f"- {st.test_id} {st.name} (flakiness: {st.flakiness_rate:.2f}, no unique coverage)"


def _fmt_flaky_critical(st: ScoredTest) -> str:
    reason = st.flaky_critical_reason or ""
    return (
        f"- {st.test_id} {st.name} "
        f"(flakiness: {st.flakiness_rate:.2f}, {reason}, "
        f"action: stabilize or replace)"
    )


def _count_flakiness_high(normalized: dict[str, Any]) -> int:
    threshold = normalized["constraints"].get("flakiness_high_tier_threshold", 0.20)
    return sum(
        1 for t in normalized.get("test_suite", [])
        if t.get("flakiness_rate", 0) > threshold
    )


def _total_exec_mins(tests: list[ScoredTest], all_tests: list[dict]) -> float:
    exec_map = {t["id"]: t.get("execution_time_secs", 0) / 60.0 for t in all_tests}
    return sum(exec_map.get(s.test_id, 0.0) for s in tests if not s.is_manual)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_report(
    normalized: dict[str, Any],
    classifications: dict[str, Any],
    tier_result: TierResult,
) -> str:
    """Render a structured markdown report from scoring results.

    Produces all 7 required sections with all 8 required labels.
    """
    sprint_risk: str = classifications.get("sprint_risk_level", "unknown")
    nfr_elevation: bool = classifications.get("nfr_elevation_required", False)
    all_tests: list[dict] = normalized.get("test_suite", [])
    budget_mins: float = normalized["constraints"].get("time_budget_mins", 60)

    flakiness_high_count = _count_flakiness_high(normalized)
    must_run_exec = _total_exec_mins(tier_result.must_run, all_tests)
    overflow_value = "Yes" if tier_result.budget_overflow else "No"
    nfr_value = "Yes" if nfr_elevation else "No"

    lines: list[str] = []

    # ------------------------------------------------------------------
    # Section 1: Optimisation Summary
    # ------------------------------------------------------------------
    lines.append("## Optimisation Summary")
    lines.append("")
    lines.append("Recommendation Mode: deterministic")
    lines.append(f"Sprint Risk Level: {sprint_risk}")
    lines.append(f"Total Must-Run: {len(tier_result.must_run)}")
    lines.append(f"Total Flaky Critical: {len(tier_result.flaky_critical)}")
    lines.append(f"Total Retire Candidates: {len(tier_result.retire)}")
    lines.append(f"NFR Elevation: {nfr_value}")
    lines.append(f"Budget Overflow: {overflow_value}")
    lines.append("")

    # ------------------------------------------------------------------
    # Section 2: Must-Run
    # ------------------------------------------------------------------
    lines.append("## Must-Run")
    lines.append("")
    if tier_result.must_run:
        for st in tier_result.must_run:
            lines.append(_fmt_test(st))
    else:
        lines.append("_No tests in this tier._")
    lines.append("")

    # ------------------------------------------------------------------
    # Section 2b: Flaky Critical Coverage
    # ------------------------------------------------------------------
    rerun_max: int = normalized["constraints"].get("flaky_critical_rerun_max", 2)
    lines.append("## Flaky Critical Coverage")
    lines.append("")
    if tier_result.flaky_critical:
        lines.append(
            "These tests cover sprint-impacted areas with unique coverage but are too "
            "unreliable to serve as clean release gates. Execute them, but do not block "
            f"on a single failure. Recommended: rerun up to {rerun_max} times on failure."
        )
        lines.append("")
        for st in tier_result.flaky_critical:
            lines.append(_fmt_flaky_critical(st))
        lines.append("")
        lines.append(
            "Stabilisation is required. These tests cannot be retired without leaving "
            "critical areas uncovered."
        )
    else:
        lines.append("_No flaky-critical tests._")
    lines.append("")

    # ------------------------------------------------------------------
    # Section 3: Should-Run If Time Permits
    # ------------------------------------------------------------------
    lines.append("## Should-Run If Time Permits")
    lines.append("")
    if tier_result.should_run:
        for st in tier_result.should_run:
            lines.append(_fmt_test(st))
    else:
        lines.append("_No tests in this tier._")
    lines.append("")

    # ------------------------------------------------------------------
    # Section 4: Defer To Overnight Run
    # ------------------------------------------------------------------
    lines.append("## Defer To Overnight Run")
    lines.append("")
    if tier_result.defer:
        for st in tier_result.defer:
            lines.append(_fmt_test(st))
    else:
        lines.append("_No tests in this tier._")
    lines.append("")

    # ------------------------------------------------------------------
    # Section 5: Retire Candidates
    # ------------------------------------------------------------------
    lines.append("## Retire Candidates")
    lines.append("")
    if tier_result.retire:
        for st in tier_result.retire:
            lines.append(_fmt_retire(st))
    else:
        lines.append("_No retire candidates._")
    lines.append("")

    # ------------------------------------------------------------------
    # Section 6: Suite Health Summary
    # ------------------------------------------------------------------
    lines.append("## Suite Health Summary")
    lines.append("")
    lines.append(f"Flakiness Tier High: {flakiness_high_count} tests above threshold")
    lines.append(f"Total automated execution time (must-run): {must_run_exec:.0f} min")
    lines.append(f"Time budget: {budget_mins:.0f} min")
    lines.append("")

    return "\n".join(lines)
