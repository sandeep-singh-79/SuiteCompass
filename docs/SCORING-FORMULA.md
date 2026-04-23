# Scoring Formula Deep-Dive

A complete derivation of how SuiteCompass assigns a numeric priority score to every test. Read this when you want to understand why a specific test landed in a specific tier, or when you want to reason about how input changes affect output.

---

## The Full Formula

$$
\text{score} = \underbrace{10 \times d_m}_{\text{direct}} + \underbrace{5 \times p_m}_{\text{dependency}} + \underbrace{3 \times e}_{\text{exploratory}} - \underbrace{8 \times f}_{\text{flakiness penalty}}
$$

| Symbol | Name | Range | Source |
|---|---|---|---|
| $d_m$ | direct risk multiplier | 0.0, 0.3, 0.6, 1.0 | highest-risk story whose `changed_areas` overlap the test's `coverage_areas` |
| $p_m$ | dependency risk multiplier | 0.0, 0.15, 0.30, 0.50 | dep story's own risk multiplier × 0.5 (independent of $d_m$) |
| $e$ | exploratory match | 0 or 1 | 1 if any `coverage_area` appears in any exploratory session's `risk_areas` |
| $f$ | flakiness rate | 0.0 – 1.0 | `flakiness_rate` field on the test |

---

## Component 1 — Direct Coverage Score (0–10)

```
direct_score = 10.0 × direct_risk_multiplier
```

The direct risk multiplier is determined by story risk:

| Story `risk` | Multiplier | Direct score |
|---|---|---|
| `high` | 1.0 | **10.0** |
| `medium` | 0.6 | **6.0** |
| `low` | 0.3 | **3.0** |
| no overlap | 0.0 | **0.0** |

**Rule:** If a test's `coverage_areas` overlap with multiple stories, only the highest-risk story counts.

**Example:** Test covers `[PaymentService, OrderFacade]`. Story A (`risk: high`) changes `[PaymentService]`. Story B (`risk: low`) changes `[OrderFacade]`. Direct multiplier = 1.0 → direct score = **10.0**.

---

## Component 2 — Dependency Coverage Score (0–5)

```
dep_score = 5.0 × dep_risk_multiplier
dep_risk_multiplier = dep_story_risk_multiplier × 0.5
```

Dependency stories are resolved at input load time from `dependency_stories` IDs. A test scores via this component when its `coverage_areas` overlap the changed areas of a *dependency* story (not the primary story).

| Dep story `risk` | Dep multiplier | Dep score |
|---|---|---|
| `high` | 1.0 × 0.5 = 0.50 | **2.5** |
| `medium` | 0.6 × 0.5 = 0.30 | **1.5** |
| `low` | 0.3 × 0.5 = 0.15 | **0.75** |

**Why the 0.5 discount?** Dependency-triggered coverage is one hop removed from the actual change. It matters, but less directly than the primary story. The discount keeps dependency tests from crowding out directly-relevant tests under budget pressure.

**Example:** Story A depends on Story B (`risk: medium`, changes `OrderFacade`). Test covers `[OrderFacade]` only. Dep multiplier = 0.3 × 0.5 = 0.15 → dep score = **0.75**. Total score = 0 + 0.75 + 0 - penalty. This typically lands in Defer — dep coverage alone rarely reaches Should-Run unless exploratory bonus also fires.

**Additive case — direct and dependency scores combine.** A test whose `coverage_areas` overlap *both* a primary story's changed areas and a dependency story's changed areas receives both scores:

```
# Test covers [SharedComponent], which appears in both Story A (direct) and Story B (dep)
direct_score = 10.0 × 1.0   = 10.0   (Story A: risk high)
dep_score    =  5.0 × 0.30  =  1.5   (Story B: risk medium, dep discount 0.5)
──────────────────────────────────────
combined before penalties    = 11.5
```

This is the most common path to high scores for shared infrastructure components — they receive both direct and dependency contributions simultaneously.

**Theoretical score range:** Minimum = −8.0 (zero coverage, max flakiness). Maximum ≈ 15.5 (high-risk direct 10.0 + high-risk dep 2.5 + exploratory 3.0 + zero flakiness). Override rules can place tests in Must-Run at any score.

---

## Component 3 — Exploratory Bonus (0 or +3)

```
exploratory_score = 3.0  # if any coverage_area ∈ any session's risk_areas
                  = 0.0  # otherwise
```

Exploratory sessions encode tester observations ("I saw timeouts in `RetryHandler` under load"). A test gets the full +3 if at least one of its coverage areas appears in any session's `risk_areas`. Multiple matching sessions do not stack — the bonus is binary.

**Why +3?** At this magnitude, the bonus can promote a medium-risk test from Should-Run (6.0) to Must-Run (9.0), but cannot by itself push a zero-coverage test into Must-Run (0 + 3 - 0 = 3.0 → Defer). Human judgement amplifies, it doesn't override.

---

## Component 4 — Flakiness Penalty (0–8)

```
flakiness_penalty = 8.0 × flakiness_rate
```

| `flakiness_rate` | Penalty | Net effect on a high-risk test (base 10.0) |
|---|---|---|
| 0.00 | 0.0 | 10.0 → Must-Run |
| 0.10 | 0.8 | 9.2 → Must-Run |
| 0.20 | 1.6 | 8.4 → Must-Run (barely) |
| 0.30 | 2.4 | 7.6 → Should-Run |
| 0.50 | 4.0 | 6.0 → Should-Run |
| 1.00 | 8.0 | 2.0 → Defer |

A very flaky test covering a high-risk story still scores above Defer (at 1.0 flakiness: 10 − 8 = 2.0 → Defer). The penalty does not override coverage signal entirely — it adjusts tier placement. A test can still be a **retire candidate** independently of its score (see retire conditions below).

---

## Tier Thresholds

| Score | Tier |
|---|---|
| ≥ 8.0 | Must-Run |
| 4.0 – 7.99 | Should-Run |
| < 4.0 | Defer |

These are hardcoded constants (`TIER_MUST_RUN = 8.0`, `TIER_SHOULD_RUN = 4.0` in `scoring_engine.py`). They are not configurable — see [PHASED-IMPLEMENTATION](PHASED-IMPLEMENTATION.md) for the rationale.

---

## Override Rules (score-independent)

Two override rules place tests in Must-Run regardless of their score:

### Mandatory Tag Override
```
if mandatory_tags ∩ test.tags ≠ ∅  →  Must-Run [override: mandatory-tag:TAG]
```
Configured via `constraints.mandatory_tags` in the input. Common use: `critical-flow`, `smoke`, `regulatory`. Override tests are **budget-exempt** — they are never demoted even under budget overflow.

### NFR Elevation Override
```
if sprint_risk == "high" AND test.layer ∈ {performance, security}
    →  Must-Run [override: nfr-elevation]
```
Fires when any story in the sprint has `risk: high`. All performance-layer and security-layer tests are promoted unconditionally. Also budget-exempt.

---

## Budget Overflow and Demotion

After initial tiering, the budget constraint is applied **only to scored must-run tests** (not overrides):

```
while sum(execution_time_secs / 60 for automated must-run)  >  time_budget_mins:
    demote the lowest-scored automated must-run test → Should-Run
```

Manual tests (`automated: false`) never count against the budget. Override tests are never demoted.

---

## Retire Conditions (independent of score)

A test is flagged as a retire candidate iff **all three** of the following are true:

1. `automated: true`
2. `flakiness_rate > flakiness_retire_threshold` (default 0.30)
3. **No unique coverage** — none of its `coverage_areas` are covered by only one test

Condition 3 prevents retiring the only test that covers a specific area. A flaky test with unique coverage lands in Defer, not Retire — it needs fixing, not removal.

Retire candidates are evaluated **before** tiering: a test flagged for retirement does not appear in Must-Run/Should-Run/Defer even if its score would qualify.

---

## Stability Score (classification-only, not rendered)

The classifier computes a per-test stability score:

```
stability_score = 1.0 - (0.7 × flakiness_rate + 0.3 × min(failure_count_last_30d / 10, 1.0))
```

This value is **not used in scoring, tiering, or any report output**. It is an internal classification artefact computed during context analysis and available for future rendering extensions. It does not appear anywhere in the Markdown report — the flakiness penalty in the main formula serves as the report-visible signal.

---

## Post-Scoring Classification — Flaky-Critical

Flaky-critical is a **post-scoring classification**, not a scored tier. It fires after `raw_score` is computed and after retire candidates are identified, but before final tier assignment.

### Why it cannot be derived from raw_score

A flaky-critical test's score may land anywhere in the scoring range. A test can be flaky-critical with a score of 1.5 (defer range) if:
- it has direct coverage of a high-risk story (raw contribution: 10.0)
- but its flakiness rate is 0.9 (penalty: −7.2)
- yielding raw_score = 2.8 → normally Defer

The scoring formula deliberately penalises flakiness. If the classification relied on `raw_score ≥ threshold`, this test would be deferred and its unique coverage silently lost. The post-scoring check bypasses the score and applies independent criteria.

### Classification logic (pseudocode)

```
for each test not already in retire_candidates:
    if (
        test.automated == True
        AND test.flakiness_rate > constraints.flakiness_high_tier_threshold
        AND test.coverage_areas ∩ any_story.changed_areas ≠ ∅  (story.risk in {medium, high})
        AND test has unique coverage
    ):
        → flaky_critical list (not placed in scored tiers)
```

### Interaction with other rules

- Flaky-critical tests are **never** retire candidates (unique coverage prevents retirement)
- Flaky-critical tests are **budget-exempt** (same exemption as overrides)
- Manual tests (`automated: false`) are **excluded** from flaky-critical consideration
- A flaky-critical test is removed from the scored-tier lists — it appears only in the `## Flaky Critical Coverage` section

---

## Worked Examples

### Example A — High-risk direct coverage, clean test

Input:
- Story: `risk: high`, `changed_areas: [PaymentService]`
- Test: `coverage_areas: [PaymentService]`, `flakiness_rate: 0.02`, no tags

```
direct_score      = 10.0 × 1.0 = 10.0
dep_score         = 0.0         (no dep overlap)
exploratory_score = 0.0         (no matching session)
flakiness_penalty = 8.0 × 0.02 = 0.16
─────────────────────────────────────────
score = 10.0 + 0.0 + 0.0 − 0.16 = 9.84  →  Must-Run
```

### Example B — Dependency coverage only, no direct overlap

Input:
- Story A depends on Story B (`risk: medium`, `changed_areas: [OrderFacade]`)
- Test: `coverage_areas: [OrderFacade]`, `flakiness_rate: 0.00`

```
direct_score      = 0.0         (test doesn't cover Story A's areas)
dep_score         = 5.0 × (0.6 × 0.5) = 5.0 × 0.3 = 1.5
exploratory_score = 0.0
flakiness_penalty = 0.0
─────────────────────────────────────────
score = 1.5  →  Defer
```

### Example C — Exploratory bonus promotes to Must-Run

Input:
- Story: `risk: medium`, `changed_areas: [RetryHandler]`
- Exploratory session: `risk_areas: [RetryHandler]`
- Test: `coverage_areas: [RetryHandler]`, `flakiness_rate: 0.05`

```
direct_score      = 10.0 × 0.6 = 6.0
dep_score         = 0.0
exploratory_score = 3.0         (RetryHandler ∈ session.risk_areas)
flakiness_penalty = 8.0 × 0.05 = 0.4
─────────────────────────────────────────
score = 6.0 + 3.0 − 0.4 = 8.6  →  Must-Run
```
Without the exploratory session: 6.0 − 0.4 = **5.6 → Should-Run**. The +3 bonus was the deciding factor.

### Example D — Flaky high-risk test: two outcomes depending on unique coverage

Input:
- Story: `risk: high`, `changed_areas: [Checkout]`
- Test: `coverage_areas: [Checkout]`, `flakiness_rate: 0.32`

```
direct_score      = 10.0 × 1.0 = 10.0
flakiness_penalty = 8.0 × 0.32 = 2.56
─────────────────────────────────────────
raw score = 7.44
```

**Case 1 — test has unique coverage** (it is the only test covering `Checkout`):
Retire check passes (condition 3 fails — unique coverage exists). Score 7.44 → **Should-Run**.
Action: fix the flakiness. This test cannot be retired without leaving Checkout uncovered.

**Case 2 — test has no unique coverage** (another test also covers `Checkout`):
Retire check: `automated: true` ✓, `flakiness_rate 0.32 > threshold 0.30` ✓, no unique coverage ✓ → **Retire Candidate**.
The raw score of 7.44 is never used — retire evaluation happens before tiering. The test does not appear in any scored tier.

---

## History Precedence

When `--history-dir` or `--history-file` is supplied, the history-derived `flakiness_rate` takes precedence over the value in the input YAML.

**Rule:** If `history.flakiness_rate != yaml.flakiness_rate`, the history value is used **everywhere** — retire threshold check, flakiness penalty in the scoring formula, and the suite health summary.

**Why history wins:** CI history is measured, not estimated. YAML values are authoring-time guesses. History is more current by definition.

**Warning emission:** When a history override occurs, a `[history-override]` warning is printed to stderr. This makes the override visible to the operator without affecting the deterministic markdown report.

**Example:**

| Source | `flakiness_rate` | Retire check (threshold 0.30) |
|---|---|---|
| YAML input | 0.05 | below threshold → not a retire candidate |
| CI history (10 runs, 5 failures) | 0.50 | above threshold → retire candidate |
| **Result with history applied** | **0.50** | **retire candidate** |

The scoring formula in this case becomes:
```
flakiness_penalty = 8.0 × 0.50 = 4.0    # history value used
```
The `[history-override]` warning on stderr: `test_id='T-001': flakiness_rate 0.050 → 0.500 (history wins)`

**Timestamp scope:** Timestamps are read from `<testsuite>` elements only. `failure_count_last_30d` counts failures from runs within 30 calendar days of today (based on the `timestamp` attribute). Runs with no parseable timestamp are included conservatively (counted as within 30 days).
