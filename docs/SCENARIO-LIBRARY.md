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

---

## 2. Low-Risk Bugfix Sprint

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

---

## 3. Degraded Suite / High Flakiness

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

---

## 4. Tight Budget Sprint

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

---

## 5. Exploratory-Driven Sprint

### Context

Exploratory testing has identified specific risk areas that the test suite should emphasise. The sprint stories are medium-risk but exploratory findings amplify specific tests' priority.

### Key Input Properties

- Stories with `risk: medium` changing broad areas
- 1-2 exploratory sessions with `risk_areas` targeting specific subsystems
- Tests covering those risk_areas get +3 exploratory bonus
- Without the bonus, these tests might only reach should-run; with it, they reach must-run

### Expected Behaviour

- Tests matching exploratory `risk_areas` score higher (+3 bonus)
- This can promote tests from should-run → must-run that otherwise wouldn't qualify
- **NFR Elevation:** `No` (sprint risk is medium, not high)
- The overall report may show more must-run tests than the raw story coverage would suggest

### Tradeoffs

Exploratory sessions encode human judgement about emerging risks. The +3 amplification is deliberate — it allows tester observations to influence automated prioritisation without overriding the entire formula.

---

## 6. Manual-Heavy Suite

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

---

## 7. Dependency Chain Sprint

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
