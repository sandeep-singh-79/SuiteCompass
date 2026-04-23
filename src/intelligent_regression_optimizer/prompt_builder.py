"""Prompt builder for LLM narrative generation."""
from __future__ import annotations

from typing import Any

from intelligent_regression_optimizer.models import TierResult
from intelligent_regression_optimizer.template_loader import load_template


def _select_scenario(classifications: dict[str, Any], tier_result: TierResult) -> str:
    if classifications.get("sprint_risk_level") == "high":
        return "high_risk"
    if classifications.get("suite_health") == "degraded":
        return "degraded_suite"
    if classifications.get("time_pressure") == "tight" and tier_result.budget_overflow:
        return "budget_pressure"
    return "balanced"


def _format_tier_assignments(tier_result: TierResult, rerun_max: int = 2) -> str:
    lines = []
    for test in tier_result.must_run:
        override = f" [override: {test.override_reason}]" if test.is_override and test.override_reason else ""
        lines.append(f"  MUST-RUN: {test.test_id} {test.name} (score: {test.raw_score:.1f}){override}")
    for test in tier_result.should_run:
        override = f" [override: {test.override_reason}]" if test.is_override and test.override_reason else ""
        lines.append(f"  SHOULD-RUN: {test.test_id} {test.name} (score: {test.raw_score:.1f}){override}")
    for test in tier_result.defer:
        override = f" [override: {test.override_reason}]" if test.is_override and test.override_reason else ""
        lines.append(f"  DEFER: {test.test_id} {test.name} (score: {test.raw_score:.1f}){override}")
    for test in tier_result.retire:
        lines.append(f"  RETIRE: {test.test_id} {test.name} (flakiness: {test.flakiness_rate:.2f})")
    for test in tier_result.flaky_critical:
        reason = f", {test.flaky_critical_reason}" if test.flaky_critical_reason else ""
        lines.append(
            f"  FLAKY-CRITICAL: {test.test_id} {test.name}"
            f" (flakiness: {test.flakiness_rate:.2f}{reason})"
        )
    if tier_result.flaky_critical:
        lines.append(f"  FLAKY-CRITICAL RERUN MAX: {rerun_max}")
    return "\n".join(lines) if lines else "  (no tests)"


def _format_stories(normalized: dict[str, Any]) -> str:
    stories = normalized.get("sprint_context", {}).get("stories", [])
    lines = [
        f"  {s.get('id', '?')} risk={s.get('risk', '?')} areas={s.get('changed_areas', [])}"
        for s in stories
    ]
    return "\n".join(lines) if lines else "  (none)"


def _flakiness_high_count(normalized: dict[str, Any]) -> int:
    threshold = normalized["constraints"].get("flakiness_high_tier_threshold", 0.20)
    return sum(
        1 for t in normalized.get("test_suite", [])
        if t.get("flakiness_rate", 0) > threshold
    )


def _must_run_exec_mins(tier_result: TierResult, normalized: dict[str, Any]) -> float:
    exec_map = {t["id"]: t.get("execution_time_secs", 0) / 60.0 for t in normalized.get("test_suite", [])}
    return sum(exec_map.get(s.test_id, 0.0) for s in tier_result.must_run if not s.is_manual)


def build_prompt(
    normalized: dict[str, Any],
    classifications: dict[str, Any],
    tier_result: TierResult,
) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) for LLM generation.

    Scenario routing priority: high_risk > degraded_suite > budget_pressure > balanced.
    All input fields are included in the user prompt (no silent omission).
    """
    system_prompt = load_template("system")
    scenario = _select_scenario(classifications, tier_result)
    template = load_template(scenario)

    constraints = normalized.get("constraints", {})
    history_source = normalized.get("_meta", {}).get("history_source", "input (YAML)")
    user_prompt = template.format(
        sprint_risk_level=classifications.get("sprint_risk_level", "unknown"),
        suite_health=classifications.get("suite_health", "unknown"),
        time_pressure=classifications.get("time_pressure", "unknown"),
        nfr_elevation_required=classifications.get("nfr_elevation_required", False),
        time_budget_mins=constraints.get("time_budget_mins", 60),
        budget_overflow=tier_result.budget_overflow,
        changed_areas=list({
            area
            for s in normalized.get("sprint_context", {}).get("stories", [])
            for area in s.get("changed_areas", [])
        }),
        stories_summary=_format_stories(normalized),
        tier_assignments=_format_tier_assignments(tier_result, rerun_max=constraints.get("flaky_critical_rerun_max", 2)),
        total_tests=len(normalized.get("test_suite", [])),
        flakiness_high_count=_flakiness_high_count(normalized),
        must_run_exec_mins=f"{_must_run_exec_mins(tier_result, normalized):.0f}",
        history_source=history_source,
    )
    return system_prompt, user_prompt
