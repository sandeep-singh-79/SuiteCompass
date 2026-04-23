# Decision Rules

Machine-checkable scoring, tiering, override, and retire rules used by SuiteCompass. This document defines the complete deterministic decision logic — no ambiguity, no prose-only descriptions.

---

## Scoring Formula

Every test receives a `raw_score` computed as:

$$
\text{raw\_score} = (10 \times \text{direct\_coverage} \times \text{risk\_multiplier}) + (5 \times \text{dep\_coverage} \times \text{dep\_risk\_multiplier}) + (3 \times \text{exploratory\_match}) - (8 \times \text{flakiness\_rate})
$$

### Term Definitions

| Term | Definition |
|---|---|
| `direct_coverage` | 1 if any of the test's `coverage_areas` intersects with a story's `changed_areas`; else 0 |
| `dep_coverage` | 1 if any `coverage_areas` intersects with a dependency story's `changed_areas`; else 0 |
| `exploratory_match` | 1 if any `coverage_areas` appears in any exploratory session's `risk_areas`; else 0 |
| `risk_multiplier` | Based on the story's `risk` level (see table below) |
| `dep_risk_multiplier` | Same risk scale × 0.5 discount |
| `flakiness_rate` | The test's declared flakiness rate (0.0 – 1.0) |

### Risk Multipliers

| Story Risk | Multiplier | Dependency Multiplier |
|---|---|---|
| `high` | 1.0 | 0.5 |
| `medium` | 0.6 | 0.3 |
| `low` | 0.3 | 0.15 |

### Multi-Story Scoring

When multiple stories cover the same test, the test receives contributions from **each** covering story. The formula applies per-story, and contributions accumulate.

### Exploratory Session Amplification

If any exploratory session's `risk_areas` matches any of the test's `coverage_areas`, the test receives a +3 bonus. This applies once per test regardless of how many sessions match.

---

## Tier Thresholds

| Tier | Condition |
|---|---|
| must-run | `raw_score ≥ 8.0` OR has an active override |
| should-run | `4.0 ≤ raw_score < 8.0` |
| defer | `raw_score < 4.0` |
| retire | Meets all three retire candidate criteria (see below) |

**Priority order:** retire check → override check → score-based tiering.

---

## Override Rules

### Mandatory Tag Override

A test is a **mandatory-tag override** if any of its `tags` matches an entry in `constraints.mandatory_tags`.

- Override reason: `mandatory-tag:{matching_tag}`
- Always placed in must-run, regardless of score
- Exempt from time budget

### NFR Elevation Override

When `sprint_risk_level == high`, all tests with `layer` in `{performance, security}` receive an NFR elevation override.

- Override reason: `nfr-elevation`
- Always placed in must-run, regardless of score
- Exempt from time budget

### Override Budget Exemption

All override-based must-run tests are **exempt** from the time budget calculation. Only scored must-run tests (those placed in must-run by raw_score ≥ 8.0, without an override) are subject to budget constraint.

---

## Retire Candidate Rules

A test becomes a **retire candidate** when ALL three conditions are true:

1. `automated == true` — manual tests are never retire candidates
2. `flakiness_rate > constraints.flakiness_retire_threshold`
3. **No unique coverage** — none of the test's `coverage_areas` are unique to that test (i.e. at least one other test in the suite covers each of its areas)

### Unique Coverage Definition

A test has **unique coverage** if at least one of its `coverage_areas` is not covered by any other test in the `test_suite`. This is a global suite property computed before tiering.

---

## Budget Overflow Rule

After initial tier assignment:

1. Sum `execution_time_secs` for all **scored** must-run tests (override tests are excluded)
2. If total exceeds `constraints.time_budget_mins × 60`:
   - Sort scored must-run tests by `raw_score` ascending
   - Demote the lowest-scored test to should-run
   - Repeat until total ≤ budget or no scored must-run tests remain
3. Set `Budget Overflow: Yes` if any demotion occurred

---

## Manual Test Rules

Tests with `automated: false`:

- **Scored and tiered** normally (same formula, same thresholds)
- **Excluded from budget calculation** — their execution time does not count against `time_budget_mins`
- **Never retire candidates** — even if flakiness is above threshold
- **Tagged `(manual)` in output** — visible in the rendered report

---

## Classification Dimensions

The context classifier derives these dimensions before scoring:

### Sprint Risk Level

```
if any story.risk == "high" → "high"
elif any story.risk == "medium" → "medium"
else → "low"
```

### NFR Elevation Required

```
nfr_elevation_required = (sprint_risk_level == "high")
```

### Suite Health

```
high_flakiness_count = count(tests where flakiness_rate > flakiness_high_tier_threshold)
ratio = high_flakiness_count / total_test_count

if no tests in suite → "unknown"
elif ratio > 0.20 → "degraded"
elif ratio < 0.05 → "stable"
else → "moderate"
```

### Time Pressure

```
total_execution = sum(execution_time_secs for all tests)
budget_secs = time_budget_mins × 60
multiple = total_execution / budget_secs

if multiple > 3.0 → "tight"
elif multiple > 1.5 → "moderate"
else → "relaxed"
```

### Per-Test Stability

```
stability = 1.0 - (0.7 × flakiness_rate + 0.3 × min(failure_count_last_30d / 10, 1.0))
# Clamped to [0.0, 1.0]
```

---

## Dependency Traversal

- **1-hop only** — dependency_stories references are resolved once; transitive dependencies are not followed.
- Each `dependency_stories` ID must reference a story defined in the same `sprint_context.stories`.
- The dependency story's `changed_areas` contribute to `dep_coverage` using the dependency's risk level (× 0.5 discount).

---

## Flaky-Critical Classification

A **flaky-critical** test is a cross-cutting classification applied *after* scoring. It is not a scored tier — it is an execution directive that overrides tier placement for a specific set of tests.

### Qualification Criteria (all four must be true)

| # | Criterion | Field / threshold |
|---|---|---|
| 1 | Test is automated | `automated: true` |
| 2 | Flakiness rate exceeds the high-tier threshold | `flakiness_rate > constraints.flakiness_high_tier_threshold` (default 0.20) |
| 3 | Test has direct coverage of a sprint story's changed areas | `coverage_areas ∩ story.changed_areas ≠ ∅` for a story with `risk: medium` or `risk: high` |
| 4 | Test has unique coverage | at least one `coverage_area` not covered by any other test in the suite |

### Decision Table

| flakiness > threshold | covers story area | unique coverage | Automated | Result |
|---|---|---|---|---|
| Yes | Yes | Yes | Yes | **Flaky-Critical** |
| Yes | Yes | No | Yes | Retire candidate (no unique coverage) |
| Yes | No | Yes | Yes | Scored tier (no story coverage) |
| No | Yes | Yes | Yes | Scored tier (not flaky enough) |
| Any | Any | Any | No (manual) | Scored tier (manual tests exempt) |

### Execution Rules

- **Always execute** — flaky-critical tests must run every sprint regardless of budget
- **Budget-exempt** — never counted against `time_budget_mins` and never demoted by budget overflow
- **Never gates release** — these tests are flagged for investigation, not for blocking
- **Rerun on failure** — the report recommends rerunning up to `constraints.flaky_critical_rerun_max` times (default 2) before treating a failure as confirmed
- **Stabilize or replace** — the report emits a `stabilize or replace` action for every flaky-critical test to prompt the team to invest in fixing the test or replacing it with a stable equivalent
- **Dedicated report section** — rendered under `## Flaky Critical Coverage`, separate from Must-Run and the scored tiers
- **Does not affect retire decisions** — a test that meets flaky-critical criteria is NOT a retire candidate (unique coverage prevents retirement)

### Pipeline Position

Flaky-critical classification runs after the retire check and before final tier assignment:

```
6. Identify retire candidates
6a. Identify flaky-critical tests (post-retire, pre-tier)
7. Apply overrides (mandatory tag, NFR elevation)
8. Assign initial tiers  (flaky-critical tests placed in flaky_critical list, not scored tiers)
```

---

## Decision Pipeline (execution order)

```
1.  Load and validate input
2.  Resolve dependency stories (1-hop)
3.  Classify context (5 dimensions)
4.  Compute unique coverage map (global)
5.  Score every test (raw_score formula)
6.  Identify retire candidates
6a. Identify flaky-critical tests (post-retire, pre-tier)
7.  Apply overrides (mandatory tag, NFR elevation)
8.  Assign initial tiers  (flaky-critical tests placed in flaky_critical list)
9.  Apply budget constraint (demote lowest-scored must-run; flaky-critical exempt)
10. Compute situational warnings
11. Render report
12. Validate output contract
```

---

## Warnings System

After tiering and budget constraint, `_compute_warnings()` inspects the final tier state and emits advisory warning strings. Warnings do **not** change any tier assignment — they surface information about silent decisions that happened during scoring.

Warnings are rendered in the `## Warnings` section of the report. Each warning has a stable ID prefix (e.g. `[COVERAGE-GAP]`) so teams can filter or suppress by ID.

### Warning IDs

| ID | Condition |
|---|---|
| `COVERAGE-GAP` | For a medium/high-risk story area, every test covering that area has been retired — leaving the area uncovered |
| `OVERRIDE-BUDGET` | Override-only execution time exceeds the configured budget (overrides are exempt from demotion, so the team should be aware) |
| `UNIQUE-DEMOTED` | Budget constraint demoted a test that holds unique coverage for a sprint area — that area is now unverified |
| `NO-MUST-RUN-COVERAGE` | A high-risk story has no must-run test covering its changed areas |
| `ZERO-BUDGET` | `time_budget_mins` is 0; all scored must-run tests were demoted |
| `NFR-NO-OVERLAP` | One or more NFR-elevated tests have no coverage overlap with any sprint story's changed areas |
| `FLAKINESS-REVERSED` | A test covers a high-risk story but its flakiness penalty dropped its score below the must-run threshold |

### Warning Guarantee

The `## Warnings` section is always present in the report. If no warnings fired, it renders `_No warnings._`.
