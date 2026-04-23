# V1 Output Template

Annotated reference for the SuiteCompass optimisation report. The output is a structured markdown document with **8 required sections** and 8 machine-checkable labels.

---

## Output Principles

1. **Structured** — fixed section order with line-anchored headings
2. **Deterministic** — same input always produces the same output
3. **Machine-checkable** — all labels and headings validated by `output_validator.py`
4. **Section-aware** — each label appears exactly once in its declared section
5. **Actionable** — each section maps directly to a team decision

---

## Required Sections (8)

| # | Heading | Purpose |
|---|---|---|
| 1 | `## Optimisation Summary` | Sprint-level overview with key decision labels |
| 2 | `## Must-Run` | Tests that must execute this sprint (overrides + high-scorers) |
| 3 | `## Should-Run If Time Permits` | Tests to run if budget allows |
| 4 | `## Defer To Overnight Run` | Tests safe to defer to off-hours CI |
| 5 | `## Retire Candidates` | Tests recommended for removal from the suite |
| 6 | `## Flaky Critical Coverage` | Flaky tests with unique coverage that must still run |
| 7 | `## Suite Health Summary` | Aggregate health metrics for the test suite |
| 8 | `## Warnings` | Situational warnings about silent scoring decisions |

---

## Required Labels (8)

| Label | Section | Value Type | Description |
|---|---|---|---|
| `Recommendation Mode:` | Optimisation Summary | `deterministic` | Always "deterministic" in Phase 1 (no LLM) |
| `Sprint Risk Level:` | Optimisation Summary | `high` / `medium` / `low` | Highest risk level across all sprint stories |
| `Total Must-Run:` | Optimisation Summary | integer | Count of tests in must-run tier |
| `Total Retire Candidates:` | Optimisation Summary | integer | Count of retire candidate tests |
| `NFR Elevation:` | Optimisation Summary | `Yes` / `No` | Whether performance/security tests were auto-promoted |
| `Budget Overflow:` | Optimisation Summary | `Yes` / `No` | Whether time budget forced demotion of must-run tests |
| `Total Flaky Critical:` | Optimisation Summary | integer | Count of tests in the flaky-critical list |
| `Flakiness Tier High:` | Suite Health Summary | `N tests above threshold` | Count of tests above `flakiness_high_tier_threshold` |

---

## Annotated Sample Output

Generated from `iro run tests/fixtures/valid_input.yaml`:

```markdown
## Optimisation Summary

Recommendation Mode: deterministic
Sprint Risk Level: high
Total Must-Run: 3
Total Retire Candidates: 0
NFR Elevation: Yes
Budget Overflow: No
Total Flaky Critical: 1

## Must-Run

- TEST-002 retry handler integration (score: 12.8) [override: mandatory-tag:critical-flow]
- TEST-003 payment service security (score: 14.4) [override: nfr-elevation]
- TEST-001 payment flow e2e (score: 14.1)

## Should-Run If Time Permits

_No tests in this tier._

## Defer To Overnight Run

_No tests in this tier._

## Retire Candidates

_No retire candidates._

## Flaky Critical Coverage

> These tests are flaky but cover sprint story areas that no other test reaches.
> They must execute despite their flakiness. Rerun up to 2 times before treating a failure as confirmed.

- AUTH-005 session token e2e (flakiness: 0.45) [stabilize or replace] unique:[SessionStore]

## Suite Health Summary

Flakiness Tier High: 1 tests above threshold
Total automated execution time (must-run): 4 min
Time budget: 20 min

## Warnings

_No warnings._
```

---

## Section Details

### Optimisation Summary

The sprint-level control panel. Contains all 6 labels that drive team decisions:

- **Recommendation Mode** — always `deterministic` until LLM layer is added
- **Sprint Risk Level** — derived from the highest `risk` value across all stories
- **Total Must-Run** — total tests in the must-run tier (overrides + scored must-run)
- **Total Retire Candidates** — tests flagged for removal
- **NFR Elevation** — `Yes` when `sprint_risk_level == high`, which auto-promotes all `performance` and `security` layer tests to must-run
- **Budget Overflow** — `Yes` when scored must-run tests exceed the time budget and the lowest-scored are demoted

### Must-Run

Each test line shows:
```
- {id} {name} (score: {raw_score}) [override: {reason}]
```

- Override reasons: `mandatory-tag:{tag}`, `nfr-elevation`
- Tests without overrides show only the score
- Manual tests are tagged `(manual)` and included but not counted in budget

### Should-Run If Time Permits

Same format as Must-Run. These tests would ideally run but are below the must-run threshold or were demoted due to budget overflow.

### Defer To Overnight Run

Tests with raw_score < 4.0. Safe to defer to longer-running overnight CI.

### Retire Candidates

Each test line shows:
```
- {id} {name} (flakiness: {flakiness_rate}, no unique coverage)
```

A test becomes a retire candidate when ALL three conditions are met:
1. `automated == true`
2. `flakiness_rate > flakiness_retire_threshold`
3. No unique coverage (all its `coverage_areas` are also covered by other tests)

Manual tests are **never** retire candidates.

### Suite Health Summary

- **Flakiness Tier High** — count of tests above `flakiness_high_tier_threshold`
- **Total automated execution time (must-run)** — sum of `execution_time_secs` for automated must-run tests, in minutes
- **Time budget** — the configured `time_budget_mins`

### Warnings

Situational warnings surfaced by `_compute_warnings()` after tiering is complete. Always present — either warning lines or `_No warnings._`.

Warning IDs and their meaning:

| Warning ID | Triggered when |
|---|---|
| `COVERAGE-GAP` | All tests covering a medium/high-risk story area have been retired |
| `OVERRIDE-BUDGET` | Override tests alone exceed the configured time budget |
| `UNIQUE-DEMOTED` | A test with unique coverage was demoted by budget constraint |
| `NO-MUST-RUN-COVERAGE` | A high-risk story has no must-run test covering it |
| `ZERO-BUDGET` | Time budget is 0, causing all scored tests to be demoted |
| `NFR-NO-OVERLAP` | NFR-elevated test(s) have no sprint story coverage overlap |
| `FLAKINESS-REVERSED` | Flakiness reduced a test below must-run despite high-risk coverage |

Warnings are **advisory only** — they do not change tier assignments.

---

## Tier Assignment Rules

| Condition | Tier |
|---|---|
| Retire candidate (automated + flaky + no unique coverage) | retire |
| Override active (mandatory tag or NFR elevation) | must-run |
| `raw_score ≥ 8.0` | must-run |
| `4.0 ≤ raw_score < 8.0` | should-run |
| `raw_score < 4.0` | defer |

Overrides take priority — a test with an override is always must-run even if its score is below 8.0.

---

## Validation Contract

The output validator (`output_validator.py`) checks:

1. All **8** headings present, line-anchored (`line.rstrip() == heading`)
2. All 8 labels present exactly once
3. No label duplicated
4. Each label appears in its declared section (not globally)

If validation fails, `iro run` exits with code 1 (validation error).
