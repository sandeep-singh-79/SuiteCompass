# Learning Guide

A tutorial on regression suite thinking — how to prioritise, what signals matter, and how to interpret optimiser output.

This guide teaches the **domain**, not just the tool. After reading it, you should be able to make principled regression testing decisions even without SuiteCompass.

---

## 1. Why Oversized Regression Suites Hurt Delivery

### The Growth Problem

Regression suites grow by accretion. Every bug gets a test. Every feature gets coverage. But tests are rarely retired. After a year, a team may have:

- 3,000 tests taking 4 hours to run
- 15% of tests flaky (failing intermittently without code changes)
- 40% of tests covering code that hasn't changed in 6 months

### Three Concrete Harms

**CI time inflation** — long suites delay developer feedback. A 4-hour regression run means developers can't merge until end-of-day. Teams start ignoring failures or batching merges, both of which increase the risk of undetected regressions.

**Flakiness noise** — when 15% of tests are flaky, developers learn to re-run and ignore failures. This masks real regressions. By the time someone investigates, the regression is several commits old and harder to diagnose.

**Manual triage overhead** — without automated prioritisation, a tech lead must manually decide which failures matter. This is a recurring tax on the most senior people, applied every sprint.

### The Counter-Intuition

Running *fewer* well-chosen tests can catch *more* regressions than running everything. The key is choosing based on sprint context — what changed, what's risky, and what coverage matters *now*.

---

## 2. How Sprint Context Changes Test Selection

The same test suite produces different priorities in different sprints. Context factors:

### Risk Level

A story marked `risk: high` triggers aggressive testing of its changed areas. The scoring formula applies a 1.0 multiplier to coverage of high-risk areas vs. 0.3 for low-risk. A test covering a high-risk change scores 3.3× higher than covering a low-risk change.

### Coverage Area Matching

A test is relevant to a sprint only if its `coverage_areas` intersect with a story's `changed_areas`. Tests that don't cover anything touched this sprint score near zero and are correctly deferred.

### NFR Elevation

When any story is `risk: high`, all performance and security tests are auto-promoted to must-run. The reasoning: high-risk changes to critical paths are precisely when latent performance regressions and security vulnerabilities emerge. This is not optional — it's a non-functional safety net.

### Dependency Coverage

Story A depends on Story B. Story B changed `OrderFacade`. Without dependency resolution, tests covering `OrderFacade` might be deferred because they don't directly relate to Story A. With 1-hop dependency traversal, those tests receive score contributions and may reach must-run.

### Exploratory Findings

A tester ran exploratory sessions and flagged `RetryHandler` as risky (observed timeouts under load). Tests covering `RetryHandler` receive a +3 bonus, potentially promoting them from should-run to must-run. Human observation feeds the automated prioritisation.

---

## 3. Reading Suite Health Signals

Beyond per-sprint prioritisation, the optimizer surfaces aggregate health metrics:

### Flakiness Rate

**What it is:** The fraction of runs where a test fails without a code change. A rate of 0.05 means 5% of runs are spurious failures.

**Healthy:** < 0.05 for individual tests; < 5% of suite above the high threshold.

**Degraded:** > 20% of tests above the high threshold. At this point, the suite is actively harming delivery because developers routinely ignore failures.

**Action:** Flaky tests above the retire threshold with no unique coverage should be removed or fixed. Tests with unique coverage that are flaky need investment — they're covering territory nothing else reaches.

### Failure Count (30d)

A test that fails frequently (even with code changes) may indicate either:
- A test coupled to volatile code (reduce coupling or accept volatility)
- A test detecting real quality issues (keep and prioritise this area)

Combined with flakiness_rate, these form the **stability score**: `1.0 - (0.7 × flakiness_rate + 0.3 × min(failure_count/10, 1.0))`

### Unique Coverage

A test has **unique coverage** if at least one of its coverage areas is not covered by any other test. This is the most important factor in retire decisions:

- **Unique coverage present:** never retire, even if flaky — fix the flakiness instead
- **No unique coverage:** safe to retire if flakiness is above threshold

---

## 4. How to Interpret a SuiteCompass Report

### Section-by-Section Reading Guide

1. **Optimisation Summary** — your decision dashboard. Check:
   - Is NFR Elevation active? If yes, expect more must-run tests
   - Is Budget Overflow active? If yes, some tests were cut — review should-run
   - How many retire candidates? If > 0, schedule a team conversation

2. **Must-Run** — these tests must execute. Look for:
   - Override tests (tagged `[override: ...]`) — these are there by rule, not just score
   - High-score tests — these have the strongest coverage relevance
   - Manual tests tagged `(manual)` — schedule these with QA team

3. **Should-Run If Time Permits** — second priority. If you finish must-run early, run these next. If budget overflowed, check which tests were demoted here.

4. **Defer To Overnight Run** — low-relevance tests this sprint. Schedule in overnight CI. Don't skip entirely — they still provide regression safety across the full codebase.

5. **Retire Candidates** — tests the tool recommends removing. Before acting:
   - Confirm no business logic depends solely on these tests
   - Check if the flakiness is fixable (cheaper than retirement)
   - Discuss with the team — retirement is a team decision, not an automated one

6. **Suite Health Summary** — global health. If `Flakiness Tier High` is above 20% of your suite, prioritise a flakiness sprint before adding more tests.

### What NOT to Do

- Don't blindly skip all should-run tests. They're second priority, not irrelevant.
- Don't ignore budget overflow. It means your must-run list was larger than your time budget — that's a risk signal.
- Don't retire without discussion. The tool flags candidates; humans decide.

---

## 5. Common Mistakes in Regression Prioritisation

### Mistake 1: Running Everything by Default

**Pattern:** "Let's just run all 3,000 tests every sprint to be safe."

**Harm:** 4-hour feedback loops, developer disengagement, flakiness noise drowning real signals, CI costs, and the illusion of safety (running everything ≠ catching everything — it means catching nothing quickly).

**Fix:** Risk-based selection. Tests covering changed areas in high-risk stories run immediately. Everything else runs overnight.

### Mistake 2: Ignoring Flakiness Until It's Too Late

**Pattern:** "That test is flaky but we'll fix it later."

**Harm:** Each flaky test teaches developers that failures are ignorable. Once 10% of the suite is flaky, the entire failure signal is compromised. Real regressions hide in noise.

**Fix:** Track flakiness_rate per test. Tests above threshold with no unique coverage are retire candidates *now*. Tests with unique coverage that are flaky need immediate investment.

### Mistake 3: Retiring Tests Without Checking Unique Coverage

**Pattern:** "This test is flaky — remove it."

**Harm:** If that test was the only one covering a specific subsystem, removing it creates a gap. The next regression in that area goes undetected.

**Fix:** Always check unique coverage before retiring. SuiteCompass does this automatically — retire candidates always have "no unique coverage."

### Mistake 4: Confusing Automation With Quality

**Pattern:** "We automated 90% of our tests — quality is covered."

**Harm:** Automation measures *activity*, not *coverage effectiveness*. An automated suite that runs the wrong tests at the wrong time provides false confidence.

**Fix:** Automate the *right* tests and run them at the *right time*. Sprint-scoped prioritisation ensures automation effort is directed where risk actually exists.

### Mistake 5: Manual Test Invisibility

**Pattern:** "Manual tests aren't in the system so they get forgotten."

**Harm:** Critical verification steps that haven't been automated get skipped because they're not tracked alongside automated tests.

**Fix:** Include manual tests in the inventory with `automated: false`. They get scored and tiered like automated tests but don't count against the budget and are tagged `(manual)` for visibility.

---

## 6. Hands-On Exercises

### Exercise 1: Predict the Tier Change

Given the valid input from `tests/fixtures/valid_input.yaml`:

1. Change `PROJ-1100`'s risk from `high` to `low`
2. Before running: predict what happens to `TEST-003` (security layer test)
3. Run `iro run` and verify your prediction

**Expected:** Without `risk: high`, NFR elevation deactivates. TEST-003 loses its override but may still score via direct coverage. It likely drops from must-run to should-run or defer.

### Exercise 2: Create a Retire Candidate

1. Copy `tests/fixtures/valid_input.yaml` to a new file
2. Add a test with `flakiness_rate: 0.45` and `coverage_areas: [PaymentService]` (not unique — TEST-001 also covers PaymentService)
3. Predict: should this test become a retire candidate?
4. Run `iro run` and check the Retire Candidates section

**Expected:** Yes — automated, flakiness > 0.30 (threshold), and no unique coverage.

### Exercise 3: Budget Overflow

1. Copy `tests/fixtures/valid_input.yaml`
2. Reduce `time_budget_mins` to 2 (120 seconds)
3. Predict: which test gets demoted first?
4. Run `iro run` and check Budget Overflow status

**Expected:** Budget Overflow: Yes. The must-run test with the lowest raw_score is demoted to should-run. Override tests (mandatory-tag, NFR elevation) are exempt from demotion.

### Exercise 4: Exploratory Session Impact

1. Copy `tests/fixtures/valid_input.yaml`
2. Remove the `exploratory_sessions` section entirely
3. Run `iro run` — note the scores
4. Add back the exploratory session and compare

**Expected:** Tests matching the exploratory session's `risk_areas` lose the +3 bonus. Some tests may drop a tier.

### Exercise 5: Dependency Chain Discovery

1. Create an input with Story A depending on Story B
2. Story B changes `AreaX` but Story A does not
3. Add a test covering only `AreaX`
4. Predict: does that test score > 0?
5. Run and verify

**Expected:** Yes — the test scores via `dep_coverage` because Story B (a dependency of Story A) changes `AreaX`.
