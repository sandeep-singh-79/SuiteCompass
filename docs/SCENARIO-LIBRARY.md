# Scenario Library

Named scenarios that illustrate how SuiteCompass behaves under different sprint conditions. Each scenario describes the context, expected key behaviours, the resulting report shape, and tradeoffs.

---

## 1. High-Risk Feature Sprint

### Context

A sprint containing a high-risk story that modifies critical payment infrastructure. Multiple tests cover the changed areas. The suite includes performance and security tests. Budget is tight relative to total execution time.

### Key Input Properties

- 1 story with `risk: high` targeting `PaymentService`, `RetryHandler`
- 1 dependency story with `risk: medium`
- Performance and security layer tests covering `PaymentService`
- Exploratory session flagging `RetryHandler`
- `time_budget_mins` significantly less than total must-run execution time

### Expected Behaviour

- **Sprint Risk Level:** `high`
- **NFR Elevation:** `Yes` — performance and security tests auto-promoted to must-run
- **Budget Overflow:** likely `Yes` — NFR override tests are budget-exempt, but scored must-run tests may exceed budget
- **Must-Run** contains: tests covering PaymentService + RetryHandler (by score/override), all perf/security tests (NFR elevation), any `critical-flow` tagged tests (mandatory tag override)
- **Retire Candidates:** flaky tests without unique coverage may appear

### Tradeoffs

Tight budget forces tradeoffs: the team must acknowledge that some scored must-run tests were demoted. NFR elevation is non-negotiable in high-risk sprints — it protects against latent performance/security regressions when critical code changes.

### Try It

A runnable benchmark is provided for this scenario:

```bash
iro benchmark benchmarks/high-risk-feature-sprint.input.yaml \
              benchmarks/high-risk-feature-sprint.assertions.yaml
# Expected: OK — 21 checks passed.
```

### Expected Output

```
Sprint Risk Level:     high
NFR Elevation:         Yes
Budget Overflow:       No
Total Must-Run:        5  (4 automated + 1 manual)
Total Retire Candidates: 0
Automated time:        18 min  (budget: 20 min)
```

Key signals to observe:
- 2 NFR override tests (performance + security) promoted regardless of score
- 1 mandatory-tag override (`critical-flow`) — score is irrelevant, it always runs
- 1 manual test appears in must-run but does **not** consume budget
- `TEST-006 reporting dashboard` scores −0.4 (no coverage overlap) → correctly deferred

Read `benchmarks/high-risk-feature-sprint.input.yaml` alongside the output to trace how each assertion maps to the scoring logic.

### Context

A quiet sprint with a single low-risk bugfix story. The test suite is healthy (low flakiness), and the time budget is generous.

### Key Input Properties

- 1 story with `risk: low` changing a single area
- No dependency stories
- No exploratory sessions
- `time_budget_mins` well above total execution time
- All tests have `flakiness_rate < 0.10`

### Expected Behaviour

- **Sprint Risk Level:** `low`
- **NFR Elevation:** `No`
- **Budget Overflow:** `No`
- **Must-Run** contains: only tests directly covering the changed area (if score ≥ 8.0), plus any mandatory-tagged tests
- **Should-Run / Defer:** most tests fall here due to low risk multipliers producing low scores
- **Retire Candidates:** likely none (healthy suite)

### Tradeoffs

In low-risk sprints, the optimizer correctly recommends running fewer tests. Teams should resist the urge to override this by running everything "just in case" — that defeats the purpose of risk-based prioritisation.

### Try It

A runnable benchmark is provided for this scenario:

```bash
iro benchmark benchmarks/low-risk-bugfix-sprint.input.yaml \
              benchmarks/low-risk-bugfix-sprint.assertions.yaml
# Expected: OK — 18 checks passed.
```

### Expected Output

```
Sprint Risk Level:     low
NFR Elevation:         No
Budget Overflow:       No
Total Must-Run:        0
Total Retire Candidates: 0
Automated time:        0 min  (budget: 60 min)
```

Key signals to observe:
- **Zero must-run tests** — the changed area has no tests scoring ≥ 8.0 under low-risk multipliers
- All 6 tests land in Defer; none in should-run
- Flakiness Tier High is 0 — the suite is healthy
- The 60-minute budget is irrelevant because no automated tests qualify for must-run or should-run

Notice how few tests land in must-run. Compare with the high-risk scenario to see the full range of the scoring formula.

### Context

A test suite with widespread flakiness. Many tests exceed the `flakiness_high_tier_threshold`. Some also lack unique coverage.

### Key Input Properties

- Multiple stories with mixed risk levels
- 30%+ of tests have `flakiness_rate > 0.20`
- Several tests have no unique coverage (their areas covered by other tests)
- `flakiness_retire_threshold: 0.30`

### Expected Behaviour

- **Suite Health:** `degraded`
- **Flakiness Tier High:** large number (e.g. "8 tests above threshold")
- **Retire Candidates:** tests that are automated, flaky above threshold, AND have no unique coverage
- **Must-Run** still works normally — a flaky test that covers a changed area still scores high
- The flakiness penalty (-8 × flakiness_rate) reduces scores but doesn't prevent must-run placement if coverage score is high enough

### Tradeoffs

The retire list is a signal, not an order. Teams should verify that retiring these tests doesn't remove safety nets for untested edge cases. The "no unique coverage" check prevents retiring the only test that covers a specific area.

### Try It

A runnable benchmark is provided for this scenario:

```bash
iro benchmark benchmarks/degraded-suite-high-flakiness.input.yaml \
              benchmarks/degraded-suite-high-flakiness.assertions.yaml
# Expected: OK — 19 checks passed.
```

### Expected Output

```
Sprint Risk Level:     medium
NFR Elevation:         No
Budget Overflow:       No
Total Must-Run:        1
Total Retire Candidates: 3
Flakiness Tier High:   4 tests above threshold
Automated time:        5 min  (budget: 15 min)
```

Key signals to observe:
- 3 retire candidates — all automated, flakiness 0.38–0.50, no unique coverage
- `TEST-206 flaky inventory unique check` is flaky (0.25) but has unique coverage → **not** retired, only deferred
- Only 1 test reaches must-run (score 8.9) despite medium-risk sprint — coverage area matching is strict
- `TEST-202` lands in should-run at score 6.6, below the 8.0 must-run threshold

Look at the Retire Candidates section in the output. Then open the input file and find which tests pass all three retire conditions: `automated: true`, flakiness above threshold, and no unique coverage.

### Context

A busy sprint with multiple high/medium-risk stories, many tests triggered as must-run by score, but an aggressive time budget that cannot accommodate all of them.

### Key Input Properties

- 3+ stories with `risk: high` or `medium`
- Many tests covering changed areas (scoring ≥ 8.0)
- `time_budget_mins` is 30% of total must-run execution time
- No mandatory tag overrides (so all must-run tests are scored, not budget-exempt)

### Expected Behaviour

- **Budget Overflow:** `Yes`
- **Must-Run** is trimmed: lowest-scored tests demoted to should-run until within budget
- Higher-scored tests remain in must-run (demotion starts from the bottom)
- Override tests (if any) are never demoted

### Tradeoffs

Budget overflow means the team is making a calculated risk tradeoff. The demoted tests still have non-trivial scores (≥ 8.0) — they're relevant but not the *most* relevant. Teams should monitor whether demoted tests catch regressions in overnight runs.

> **No runnable benchmark** — this is an illustrative scenario. Create your own by writing an input with many high-scoring tests and a tight budget.

### Context

Exploratory testing has identified specific risk areas that the test suite should emphasise. The sprint stories are medium-risk but exploratory findings amplify specific tests' priority.

### Key Input Properties

- Stories with `risk: medium` changing broad areas
- 1-2 exploratory sessions with `risk_areas` targeting specific subsystems

---

## Flaky-Critical Coverage Sprint

### Context

A sprint where some tests are both flaky and the *only* tests covering certain story areas. The scoring formula penalises their flakiness, but retiring them would leave those areas unverified. SuiteCompass resolves this tension via the **flaky-critical classification**: these tests must run, but the report also signals they need investment.

### Key Input Properties

- At least one story with `risk: medium` or `risk: high`
- One test (`FC-001`) with `flakiness_rate > flakiness_high_tier_threshold` (0.20), covering a story-changed area (`SessionStore`) that no other test covers — **unique coverage present**
- One test (`FC-002`) with high flakiness but **no unique coverage** (another test also covers its area) — retire candidate, not flaky-critical
- One stable test (`T-003`) that covers the changed story area normally

### Expected Behaviour

- **Total Flaky Critical:** `1` (only `FC-001` qualifies — `FC-002` retires, `T-003` is stable)
- **`## Flaky Critical Coverage`** section appears in the report with `FC-001`
- `FC-001` receives a `stabilize or replace` action
- `FC-002` appears in **Retire Candidates** (flaky + no unique coverage)
- `T-003` is scored normally and lands in Must-Run (direct coverage, high risk)

### Why FC-002 Does Not Qualify

`FC-002` covers `AuthService`, but so does `T-003`. Because `FC-002` has no unique coverage, it meets all three retire conditions (automated + flaky + no unique coverage) and is retired. It is never a flaky-critical candidate.

### Tradeoffs

Flaky-critical is a short-term execution directive, not a long-term solution. The `stabilize or replace` action is a prompt for the team to invest: either fix the root cause of the flakiness, or write a stable replacement test before retiring the flaky one. Leaving flaky-critical tests in the suite indefinitely is an anti-pattern.

### Try It

A runnable benchmark is provided for this scenario:

```bash
iro benchmark benchmarks/flaky-critical-sprint.input.yaml \
              benchmarks/flaky-critical-sprint.assertions.yaml
# Expected: OK — N checks passed.
```

### Expected Output

```
Sprint Risk Level:    high
NFR Elevation:        No
Budget Overflow:      No
Total Must-Run:       1  (T-003)
Total Flaky Critical: 1  (FC-001)
Total Retire Candidates: 1  (FC-002)
```

Key signals to observe:
- `## Flaky Critical Coverage` section is present
- `FC-001` appears in the flaky-critical section with a `stabilize or replace` action
- `FC-002` appears in Retire Candidates — not in flaky-critical — because it has no unique coverage
- `T-003` appears in Must-Run with a normal score
- Tests covering those risk_areas get +3 exploratory bonus
- Without the bonus, these tests might only reach should-run; with it, they reach must-run

### Expected Behaviour

- Tests matching exploratory `risk_areas` score higher (+3 bonus)
- This can promote tests from should-run → must-run that otherwise wouldn't qualify
- **NFR Elevation:** `No` (sprint risk is medium, not high)
- The overall report may show more must-run tests than the raw story coverage would suggest

### Tradeoffs

Exploratory sessions encode human judgement about emerging risks. The +3 amplification is deliberate — it allows tester observations to influence automated prioritisation without overriding the entire formula.

> **No runnable benchmark** — this is an illustrative scenario. See Exercise 4 in the [LEARNING-GUIDE](LEARNING-GUIDE.md) for a hands-on walkthrough.

### Context

A mixed suite where many tests are manual (automation pending). The team needs visibility into which manual tests are high-priority without counting them against the automated time budget.

### Key Input Properties

- 50%+ tests with `automated: false`
- Stories with `risk: high` changing areas covered by both manual and automated tests
- Tight `time_budget_mins`

### Expected Behaviour

- Manual tests scored and tiered normally — they appear in Must-Run / Should-Run / Defer
- Manual tests tagged with `(manual)` in output
- Manual tests are **not counted** in budget calculation
- Budget overflow calculation only considers automated must-run tests
- Manual tests are **never** retire candidates

### Tradeoffs

Manual tests represent team knowledge that hasn't been encoded into automation yet. Showing them in the report ensures teams don't lose visibility into necessary manual verification, while not letting them distort the budget constraint for the automated pipeline.

> **No runnable benchmark** — this is an illustrative scenario. Add `automated: false` to any test in an existing benchmark file to observe the behaviour.

### Context

A sprint where one story depends on another. The dependency story changes areas covered by tests that the primary story doesn't directly cover. Without dependency resolution, those tests would be missed.

### Key Input Properties

- Story A: `risk: high`, `changed_areas: [PaymentService]`, `dependency_stories: [story-B]`
- Story B: `risk: medium`, `changed_areas: [OrderFacade, PaymentService]`
- Tests covering `OrderFacade` — these are only triggered via the dependency chain

### Expected Behaviour

- Tests covering `OrderFacade` score via `dep_coverage` (5 × dep_risk_multiplier)
- dep_risk_multiplier = Story B's risk multiplier (0.6) × 0.5 = 0.3
- These tests may not reach must-run on dep scores alone, but combined with other factors they might
- Tests covering `PaymentService` score via both `direct_coverage` AND `dep_coverage`

### Tradeoffs

1-hop dependency traversal catches the most common coupling case (Story A depends on Story B; Story B's changes may break tests not directly related to Story A). Multi-hop traversal is deliberately deferred — it adds complexity without clear value for most sprint shapes.

> **No runnable benchmark** — this is an illustrative scenario. See Exercise 5 in the [LEARNING-GUIDE](LEARNING-GUIDE.md) for a hands-on walkthrough with scoring calculations.

---

## Scenario Comparison Matrix

| Scenario | Sprint Risk | NFR Elevation | Budget Overflow | Retire Candidates | Key Differentiator |
|---|---|---|---|---|---|
| High-Risk Feature | high | Yes | Likely | Possible | NFR elevation drives must-run count up |
| Low-Risk Bugfix | low | No | No | Unlikely | Most tests deferred; minimal execution |
| Degraded Suite | varies | Depends | Possible | Multiple | Retire list is the primary action item |
| Tight Budget | high/medium | Depends | Yes | Possible | Budget demotion is the key tradeoff |
| Exploratory-Driven | medium | No | Possible | Unlikely | Human judgement amplifies priority |
| Manual-Heavy | varies | Depends | Possible | Never (manual) | Budget only counts automated tests |
| Dependency Chain | varies | Depends | Possible | Possible | dep_coverage reveals hidden coupling |

---

## Common Input Mistakes

Schema and input errors that cause silent wrong results or hard-to-read validation failures.

**Wrong risk value**
```yaml
# Bad — unrecognised value is a validation error
risk: HIGH        # must be lowercase: high / medium / low
```

**Coverage areas not matching changed areas**
The most common reason a test scores zero when you expect it to be prioritised. `coverage_areas` in the test must exactly match strings in a story's `changed_areas`.
```yaml
# Story changed_areas: [PaymentService]
# Test coverage_areas: [payment_service]  ← no match — test scores 0
coverage_areas: [PaymentService]           # ← must be identical string
```

**Dependency story ID not defined in the same sprint**
```yaml
stories:
  - id: story-A
    dependency_stories: [story-X]  # story-X is not in this sprint — validation error
```

**Forgetting `automated: true` is the default**
Tests without an `automated` field are treated as automated. If a test is manual, declare it explicitly; otherwise it counts against the time budget.
```yaml
automated: false   # required to exclude from budget and tag as (manual)
```

**Mixing test layers incorrectly**
`layer` must be one of: `e2e`, `integration`, `unit`, `security`, `performance`. Any other value is a validation error. NFR elevation only triggers for `performance` and `security` layers — `perf` or `sec` will not be elevated.

For strategic mistakes (running everything, ignoring flakiness, premature retirement), see Section 5 of the [LEARNING-GUIDE](LEARNING-GUIDE.md).
