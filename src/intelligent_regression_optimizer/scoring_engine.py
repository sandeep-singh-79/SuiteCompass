"""Scoring engine for intelligent-regression-optimizer.

Implements the deterministic scoring pipeline:
  load → classify → score_tests → render

Public API: score_tests(normalized, classifications) → TierResult
"""
from __future__ import annotations

from typing import Any

from intelligent_regression_optimizer.models import ScoredTest, TierResult

# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

RISK_MULTIPLIERS: dict[str, float] = {"high": 1.0, "medium": 0.6, "low": 0.3}
DEP_DISCOUNT = 0.5

TIER_MUST_RUN = 8.0
TIER_SHOULD_RUN = 4.0

NFR_LAYERS = {"performance", "security"}

# Risks that qualify a story for flaky-critical elevation
_FLAKY_CRITICAL_RISKS = {"high", "medium"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_tests(normalized: dict[str, Any], classifications: dict[str, Any]) -> TierResult:
    """Score every test and assign it to a tier.

    Args:
        normalized:      The ``normalized`` dict from :class:`InputPackage`.
        classifications: The dict returned by :func:`classify_context`.

    Returns:
        :class:`TierResult` with must_run, should_run, defer, retire lists
        and a budget_overflow flag.
    """
    sprint = normalized["sprint_context"]
    stories: list[dict] = sprint.get("stories", [])
    exploratory: list[dict] = sprint.get("exploratory_sessions", [])
    tests: list[dict] = normalized.get("test_suite", [])
    constraints: dict = normalized.get("constraints", {})

    budget_mins: float = constraints.get("time_budget_mins", 60)
    mandatory_tags: set[str] = set(constraints.get("mandatory_tags", []))
    retire_threshold: float = constraints.get("flakiness_retire_threshold", 0.30)
    nfr_elevation: bool = classifications.get("nfr_elevation_required", False)

    # --- 1. Unique coverage map (global suite property) ---------------------
    unique_coverage: set[str] = _build_unique_coverage(tests)

    # --- 2. Score every test ------------------------------------------------
    scored: list[ScoredTest] = []
    for test in tests:
        raw = _compute_raw_score(test, stories, exploratory)
        is_manual = not test.get("automated", True)

        # Determine hard override
        override, reason = _check_override(test, mandatory_tags, nfr_elevation)

        scored.append(ScoredTest(
            test_id=test["id"],
            name=test["name"],
            raw_score=raw,
            tier="",          # filled in below
            is_override=override,
            override_reason=reason,
            is_manual=is_manual,
            flakiness_rate=test.get("flakiness_rate", 0.0),
        ))

    # --- 3. Identify retire candidates -------------------------------------
    retire_ids: set[str] = _find_retire_candidates(tests, retire_threshold, unique_coverage)

    # --- 3b. Identify flaky-critical tests ---------------------------------
    flaky_critical_ids: set[str] = _find_flaky_critical(
        tests, stories, retire_ids, unique_coverage, constraints
    )

    # --- 4. Assign initial tiers -------------------------------------------
    must_run: list[ScoredTest] = []
    should_run: list[ScoredTest] = []
    defer: list[ScoredTest] = []
    retire: list[ScoredTest] = []
    flaky_critical: list[ScoredTest] = []

    for st in scored:
        test = next(t for t in tests if t["id"] == st.test_id)

        if st.test_id in retire_ids:
            st.tier = "retire"
            retire.append(st)
            continue

        if st.is_override:
            st.tier = "must-run"
            must_run.append(st)
            continue

        if st.test_id in flaky_critical_ids:
            st.tier = "flaky-critical"
            st.is_flaky_critical = True
            st.flaky_critical_reason = _build_flaky_critical_reason(test, unique_coverage)
            flaky_critical.append(st)
            continue

        if st.raw_score >= TIER_MUST_RUN:
            st.tier = "must-run"
            must_run.append(st)
        elif st.raw_score >= TIER_SHOULD_RUN:
            st.tier = "should-run"
            should_run.append(st)
        else:
            st.tier = "defer"
            defer.append(st)

    # --- 5. Budget constraint (scored must-run only; overrides exempt) ------
    budget_overflow = False

    scored_must_run = [s for s in must_run if not s.is_override]
    override_must_run = [s for s in must_run if s.is_override]

    scored_must_run, demoted, budget_overflow = _apply_budget_constraint(
        scored_must_run, tests, budget_mins
    )

    for st in demoted:
        st.tier = "should-run"
    should_run = demoted + should_run

    must_run = override_must_run + scored_must_run

    # --- 6. Compute situational warnings -----------------------------------
    warnings = _compute_warnings(
        stories=stories,
        tests=tests,
        must_run=must_run,
        should_run=should_run,
        defer=defer,
        retire=retire,
        override_must_run=override_must_run,
        demoted=demoted,
        unique_coverage=unique_coverage,
        budget_mins=budget_mins,
        nfr_elevation=nfr_elevation,
    )

    return TierResult(
        must_run=must_run,
        should_run=should_run,
        defer=defer,
        retire=retire,
        budget_overflow=budget_overflow,
        flaky_critical=flaky_critical,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_raw_score(
    test: dict,
    stories: list[dict],
    exploratory_sessions: list[dict],
) -> float:
    """Compute the raw score for a single test."""
    coverage_areas: set[str] = set(test.get("coverage_areas", []))
    flakiness: float = test.get("flakiness_rate", 0.0)

    # Direct coverage: max risk_multiplier across sprint stories that overlap
    direct_mult = 0.0
    for story in stories:
        if coverage_areas & set(story.get("changed_areas", [])):
            risk = story.get("risk", "low")
            mult = RISK_MULTIPLIERS.get(risk, 0.0)
            direct_mult = max(direct_mult, mult)

    # Dependency coverage: max risk_multiplier × 0.5 across resolved_deps
    dep_mult = 0.0
    for story in stories:
        for dep in story.get("resolved_deps", []):
            if coverage_areas & set(dep.get("changed_areas", [])):
                risk = dep.get("risk", "low")
                mult = RISK_MULTIPLIERS.get(risk, 0.0) * DEP_DISCOUNT
                dep_mult = max(dep_mult, mult)

    # Exploratory match: 1 if any coverage_area ∈ session risk_areas
    exploratory_match = 0.0
    for session in exploratory_sessions:
        if coverage_areas & set(session.get("risk_areas", [])):
            exploratory_match = 1.0
            break

    direct_score = 10.0 * (1.0 if direct_mult > 0 else 0.0) * direct_mult
    dep_score = 5.0 * (1.0 if dep_mult > 0 else 0.0) * dep_mult
    exploratory_score = 3.0 * exploratory_match
    flakiness_penalty = 8.0 * flakiness

    return direct_score + dep_score + exploratory_score - flakiness_penalty


def _check_override(
    test: dict,
    mandatory_tags: set[str],
    nfr_elevation: bool,
) -> tuple[bool, str | None]:
    """Return (is_override, reason) for this test."""
    tags: set[str] = set(test.get("tags", []))
    if mandatory_tags & tags:
        matching = sorted(mandatory_tags & tags)
        return True, f"mandatory-tag:{','.join(matching)}"

    if nfr_elevation and test.get("layer") in NFR_LAYERS:
        return True, "nfr-elevation"

    return False, None


def _build_unique_coverage(tests: list[dict]) -> set[str]:
    """Return the set of coverage_areas that appear in exactly one test."""
    from collections import Counter
    area_counts: Counter = Counter()
    for test in tests:
        for area in test.get("coverage_areas", []):
            area_counts[area] += 1
    return {area for area, count in area_counts.items() if count == 1}


def _find_retire_candidates(
    tests: list[dict],
    retire_threshold: float,
    unique_coverage: set[str],
) -> set[str]:
    """Return ids of tests that are retire candidates.

    A test is a retire candidate iff:
    - automated == True
    - flakiness_rate > retire_threshold
    - has NO unique coverage (none of its areas are in unique_coverage)
    """
    retire_ids: set[str] = set()
    for test in tests:
        if not test.get("automated", True):
            continue
        if test.get("flakiness_rate", 0.0) <= retire_threshold:
            continue
        test_areas = set(test.get("coverage_areas", []))
        if test_areas & unique_coverage:
            continue  # has unique coverage — do not retire
        retire_ids.add(test["id"])
    return retire_ids


def _find_flaky_critical(
    tests: list[dict],
    stories: list[dict],
    retire_ids: set[str],
    unique_coverage: set[str],
    constraints: dict,
) -> set[str]:
    """Return ids of tests that qualify as flaky-critical.

    A test qualifies iff ALL of the following are true:
    1. flakiness_rate > flakiness_high_tier_threshold
    2. direct coverage overlap with at least one sprint story's changed_areas
    3. that story has risk: medium or high
    4. test has unique coverage (at least one coverage_area in unique_coverage)

    Tests already in retire_ids are excluded — retire takes precedence.
    """
    threshold: float = constraints.get("flakiness_high_tier_threshold", 0.20)
    flaky_critical_ids: set[str] = set()

    for test in tests:
        if test["id"] in retire_ids:
            continue
        if not test.get("automated", True):
            continue
        flakiness = test.get("flakiness_rate", 0.0)
        if flakiness <= threshold:
            continue
        coverage_areas: set[str] = set(test.get("coverage_areas", []))
        if not (coverage_areas & unique_coverage):
            continue
        # Check for direct coverage overlap with a medium/high risk story
        for story in stories:
            if story.get("risk") not in _FLAKY_CRITICAL_RISKS:
                continue
            if coverage_areas & set(story.get("changed_areas", [])):
                flaky_critical_ids.add(test["id"])
                break

    return flaky_critical_ids


def _build_flaky_critical_reason(test: dict, unique_coverage: set[str]) -> str:
    """Build a human-readable reason string for a flaky-critical test."""
    test_areas: set[str] = set(test.get("coverage_areas", []))
    unique_areas = sorted(test_areas & unique_coverage)
    return f"unique:{unique_areas}"


def _apply_budget_constraint(
    scored_must_run: list[ScoredTest],
    all_tests: list[dict],
    budget_mins: float,
) -> tuple[list[ScoredTest], list[ScoredTest], bool]:
    """Demote lowest-scored must-run tests until total fits within budget.

    Returns (remaining_must_run, demoted, overflow_occurred).
    Only automated tests consume budget.
    """
    exec_map: dict[str, float] = {
        t["id"]: t.get("execution_time_secs", 0) / 60.0
        for t in all_tests
        if t.get("automated", True)
    }

    budget_mins_f = float(budget_mins)
    total = sum(exec_map.get(s.test_id, 0.0) for s in scored_must_run)

    if total <= budget_mins_f:
        return scored_must_run, [], False

    # Sort ascending by raw_score — demote lowest first
    sorted_must = sorted(scored_must_run, key=lambda s: s.raw_score)
    remaining: list[ScoredTest] = list(sorted_must)
    demoted: list[ScoredTest] = []

    while total > budget_mins_f and remaining:
        candidate = remaining.pop(0)  # lowest score
        total -= exec_map.get(candidate.test_id, 0.0)
        demoted.append(candidate)

    return remaining, demoted, True


# ---------------------------------------------------------------------------
# Warning detection
# ---------------------------------------------------------------------------

def _compute_warnings(
    *,
    stories: list[dict],
    tests: list[dict],
    must_run: list[ScoredTest],
    should_run: list[ScoredTest],
    defer: list[ScoredTest],
    retire: list[ScoredTest],
    override_must_run: list[ScoredTest],
    demoted: list[ScoredTest],
    unique_coverage: set[str],
    budget_mins: float,
    nfr_elevation: bool,
) -> list[str]:
    """Detect and return situational warning strings for a sprint run."""
    warnings: list[str] = []
    retire_ids: set[str] = {s.test_id for s in retire}
    test_map: dict[str, dict] = {t["id"]: t for t in tests}

    # W5: ZERO-BUDGET — budget is 0
    if budget_mins == 0:
        warnings.append("[ZERO-BUDGET] Time budget is 0 — all scored tests were demoted.")

    # W1: COVERAGE-GAP — all tests covering a sprint area are retired
    for story in stories:
        if story.get("risk") not in {"medium", "high"}:
            continue
        for area in story.get("changed_areas", []):
            covering = [
                t for t in tests
                if area in t.get("coverage_areas", [])
            ]
            if not covering:
                continue  # No tests at all for area — different problem
            if all(t["id"] in retire_ids for t in covering):
                warnings.append(
                    f"[COVERAGE-GAP] All tests covering area '{area}'"
                    f" (story {story['id']}) have been retired."
                )

    # W2: OVERRIDE-BUDGET — override tests alone exceed budget
    override_exec_mins = sum(
        test_map[s.test_id].get("execution_time_secs", 0) / 60.0
        for s in override_must_run
        if s.test_id in test_map and test_map[s.test_id].get("automated", True)
    )
    if override_exec_mins > budget_mins > 0:
        warnings.append(
            f"[OVERRIDE-BUDGET] Override tests total {override_exec_mins:.0f} min"
            f" which exceeds the {budget_mins:.0f}-min budget."
        )

    # W3: UNIQUE-DEMOTED — budget demotion dropped a test with unique coverage
    for st in demoted:
        test = test_map.get(st.test_id, {})
        for area in test.get("coverage_areas", []):
            if area in unique_coverage:
                warnings.append(
                    f"[UNIQUE-DEMOTED] '{st.name}' (id: {st.test_id}) was demoted"
                    f" by budget constraint but holds unique coverage for area '{area}'."
                )
                break  # one warning per test is enough

    # W4: NO-MUST-RUN-COVERAGE — high-risk story has no must-run test covering it
    for story in stories:
        if story.get("risk") != "high":
            continue
        changed = set(story.get("changed_areas", []))
        if not changed:
            continue
        covered = any(
            changed & set(test_map[s.test_id].get("coverage_areas", []))
            for s in must_run
            if s.test_id in test_map
        )
        if not covered:
            warnings.append(
                f"[NO-MUST-RUN-COVERAGE] High-risk story {story['id']}"
                f" (areas: {sorted(changed)}) has no must-run test covering it."
            )

    # W7: NFR-NO-OVERLAP — NFR-elevated tests have no sprint coverage overlap
    if nfr_elevation:
        nfr_tests = [
            s for s in override_must_run
            if s.override_reason == "nfr-elevation" and s.test_id in test_map
        ]
        all_changed: set[str] = set()
        for story in stories:
            all_changed.update(story.get("changed_areas", []))
        no_overlap = [
            s for s in nfr_tests
            if not (set(test_map[s.test_id].get("coverage_areas", [])) & all_changed)
        ]
        if no_overlap:
            warnings.append(
                f"[NFR-NO-OVERLAP] {len(no_overlap)} NFR-elevated test(s) have no"
                " coverage overlap with any sprint story's changed areas."
            )

    # W8: FLAKINESS-REVERSED — flakiness pushed a high-risk-covering test below must-run
    for st in should_run + defer:
        if st.flakiness_rate <= 0:
            continue
        test = test_map.get(st.test_id, {})
        coverage = set(test.get("coverage_areas", []))
        for story in stories:
            if story.get("risk") != "high":
                continue
            if coverage & set(story.get("changed_areas", [])):
                # Would this test be must-run without flakiness?
                score_without_flakiness = st.raw_score + 8 * st.flakiness_rate
                if score_without_flakiness >= TIER_MUST_RUN:
                    warnings.append(
                        f"[FLAKINESS-REVERSED] '{st.name}' (id: {st.test_id}) covers"
                        f" high-risk story {story['id']} but flakiness"
                        f" ({st.flakiness_rate:.2f}) reduced its score below the"
                        " must-run threshold."
                    )
                    break  # one warning per test

    return warnings
