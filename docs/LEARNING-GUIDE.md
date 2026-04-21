# Learning Guide

A tutorial on regression suite thinking — how to prioritise, what signals matter, and how to interpret optimiser output.

This guide teaches the **domain**, not just the tool. After reading it, you should be able to make principled regression testing decisions even without SuiteCompass.

---

## How SuiteCompass Thinks

Every run follows the same five-step pipeline:

```
Input YAML
    │
    ▼
1. Validation ── rejects malformed inputs early (wrong types, missing keys,
    │             invalid enums, referential integrity)
    ▼
2. Classification ── reads sprint context to determine:
    │                 sprint risk level (high / medium / low)
    │                 NFR elevation flag (yes if any story is high-risk)
    │                 suite health (flakiness rates, unique coverage map)
    ▼
3. Scoring ── assigns a numeric priority score to every test:
    │          direct_coverage + dep_coverage + exploratory_bonus
    │          − flakiness_penalty − stability_penalty
    │          + mandatory/NFR overrides (budget-exempt, always must-run)
    ▼
4. Selection ── tiering by score threshold and budget:
    │            ≥ 8.0 → Must-Run  (trimmed by budget if overflow)
    │            4.0–7.9 → Should-Run
    │            < 4.0 → Defer
    │            retire conditions → Retire Candidates
    ▼
5. Rendering ── Markdown report with five sections + suite health summary
```

**What this means in practice:**
- A test with no coverage overlap to any changed story will score near zero and land in Defer — correctly.
- A test covering a high-risk story scores 3.3× higher than the same test covering a low-risk story.
- NFR elevation bypasses scoring entirely — performance and security tests run unconditionally when sprint risk is high.
- Budget overflow trims from the bottom of must-run, never from overrides.

For the complete formula derivation with worked examples, see [SCORING-FORMULA](SCORING-FORMULA.md). For writing benchmarks that validate this pipeline, see [BENCHMARK-AUTHORING](BENCHMARK-AUTHORING.md).

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

### How Flakiness is Computed from CI History (V1-A)

In earlier input formats, `flakiness_rate` and `failure_count_last_30d` were entered manually in the YAML. With `--history-dir`, SuiteCompass can derive these values automatically from a directory of JUnit XML files (one file per CI run).

**The heuristic:**

```
flakiness_rate         = flaky_failures / total_runs

A failure is "flaky" when at least one adjacent run (by filename order,
treated as chronological order) was a pass.  Consistent failures have no
adjacent pass and contribute 0 to the numerator, giving flakiness_rate = 0.0.

failure_count_last_30d = failures in runs with timestamp ≤ 30 days old
                         (runs without a timestamp are included conservatively)
```

**Examples:**

| Run sequence        | flakiness_rate | Interpretation            |
|---------------------|----------------|---------------------------|
| fail, fail, fail    | 0.0            | Consistently broken       |
| fail, pass          | 0.5            | First run flaky (adj pass)|
| fail, pass, fail    | 0.667          | Both failures are flaky   |
| pass, fail, pass    | 0.333          | Isolated mid-run failure  |

**File-order assumption:** XML files in the directory are sorted lexicographically
(`sorted()`).  Because CI systems typically name artefacts with date- or
sequence-prefixed filenames (e.g. `run-01.xml`, `2026-04-15.xml`),
lexicographic order is treated as chronological.  If your files are not named
this way, the heuristic may be unreliable.

**Supported formats:**
- pytest-junit: `<testsuite>` at the XML root (standard `pytest --junit-xml` output)
- Maven Surefire: `<testsuites>` wrapping `<testsuite>` children

**Limitations to be aware of:**
- Each XML file is treated as exactly one test run — filename order does not affect the aggregate rate
- A test absent from a file (not run, not skipped) does not contribute to `total_runs` for that file
- `<skipped>` tests are excluded from all calculations
- `<error>` elements are treated identically to `<failure>` elements
- If no timestamp is present on a `<testsuite>`, that run's failures are included in `failure_count_last_30d` conservatively (we cannot confirm it was old)
- History values take precedence over manually entered YAML values; a `[history-override]` warning is emitted for every test where the values differ

**How history is merged into the pipeline (V1-A, `merge_history()`):**

When history data is available it is merged into the normalized input *before* scoring runs:

1. For each test in `test_suite`, look up its `id` in the history dict.
2. If found: replace `flakiness_rate` with the history value; set `failure_count_last_30d` and `total_runs` from the history record.
3. If a test's YAML `flakiness_rate` differs from the history value, a `[history-override]` warning is recorded.
4. Tests not present in history are left unchanged.
5. The scoring engine then receives the merged test_suite — history-derived flakiness values affect tier placement and retire decisions exactly as if they had been typed into the YAML.

**Manual override remains available:** if CI history is unavailable or incomplete, you can still enter `flakiness_rate` directly in the YAML and omit `--history-dir`.

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

<details>
<summary><strong>Worked Solution</strong></summary>

With `risk: high` (original): TEST-003 scores as:
```
direct_coverage=1 (PaymentService ∩ PROJ-1100), risk_mult=1.0   → 10 × 1 × 1.0  = 10.0
dep_coverage=1    (PaymentService ∩ PROJ-1099), dep_risk_mult=0.3 →  5 × 1 × 0.3  =  1.5
exploratory_match=1 (PaymentService ∈ EX-07)                    →  3 × 1         =  3.0
flakiness penalty (0.01)                                        → -8 × 0.01      = -0.08
raw_score = 14.42  → must-run  +  [override: nfr-elevation]
```

After changing `PROJ-1100` risk to `low`:
```
direct_coverage=1, risk_mult=0.3    → 10 × 1 × 0.3  = 3.0
dep_coverage=1,    dep_risk_mult=0.15 →  5 × 1 × 0.15 = 0.75
exploratory_match=1                →  3 × 1         = 3.0
flakiness penalty                  → -8 × 0.01      = -0.08
raw_score = 6.67  → should-run  (≥4 but <8; NFR elevation off because sprint_risk_level is now low)
```

Key takeaway: the risk multiplier has a 3.3× swing between `high` (1.0) and `low` (0.3). NFR elevation is an all-or-nothing trigger on `sprint_risk_level == high` — changing any story's risk to low affects the whole sprint.

</details>

### Exercise 2: Create a Retire Candidate

1. Copy `tests/fixtures/valid_input.yaml` to a new file
2. Add a test with `flakiness_rate: 0.45` and `coverage_areas: [PaymentService]` (not unique — TEST-001 also covers PaymentService)
3. Predict: should this test become a retire candidate?
4. Run `iro run` and check the Retire Candidates section

**Expected:** Yes — automated, flakiness > 0.30 (threshold), and no unique coverage.

<details>
<summary><strong>Worked Solution</strong></summary>

Three retire conditions must ALL be true:

1. `automated: true` (default) ✓
2. `flakiness_rate: 0.45` > `flakiness_retire_threshold: 0.30` ✓
3. No unique coverage: the new test covers only `PaymentService`, which is also covered by TEST-001
   → PaymentService is not unique to this test ✓

All three conditions met → retire candidate.

The output line will look like:
```
- TEST-NEW your-test-name (flakiness: 0.45, no unique coverage)
```

Now try changing `coverage_areas` to a new area not covered by any other test (e.g. `[LegacyAdapter]`). The test is still flaky, but it now has **unique coverage** → no longer a retire candidate. The tool will not flag it for retirement, because retiring it would leave `LegacyAdapter` completely uncovered.

</details>

### Exercise 3: Budget Overflow

1. Copy `tests/fixtures/valid_input.yaml`
2. Reduce `time_budget_mins` to 2 (120 seconds)
3. Predict: which test gets demoted first?
4. Run `iro run` and check Budget Overflow status

**Expected:** Budget Overflow: Yes. The must-run test with the lowest raw_score is demoted to should-run. Override tests (mandatory-tag, NFR elevation) are exempt from demotion.

<details>
<summary><strong>Worked Solution</strong></summary>

Budget = 2 mins × 60 = 120 seconds.

The three must-run tests and their execution times:

| Test | Score | Time (s) | Override? |
|------|-------|----------|-----------|
| TEST-001 (payment flow e2e) | 14.10 | 120 | No |
| TEST-002 (retry handler) | 12.84 | 45 | Yes (mandatory-tag: critical-flow) |
| TEST-003 (security) | 14.42 | 90 | Yes (nfr-elevation) |

Override tests are **budget-exempt**, so only TEST-001 counts: 120s.
Budget is 120s. 120 ≤ 120 → no overflow in this specific case.

Try reducing `time_budget_mins` to 1 (60 seconds). Now TEST-001 (120s) exceeds budget alone:

- TEST-001 has no override and is the only scored must-run test
- It gets demoted to should-run
- `Budget Overflow: Yes` appears in the report

This shows that override tests (mandatory-tag, NFR elevation) are never demoted regardless of budget pressure — they represent non-negotiable quality gates.

</details>

### Exercise 4: Exploratory Session Impact

1. Copy `tests/fixtures/valid_input.yaml`
2. Remove the `exploratory_sessions` section entirely
3. Run `iro run` — note the scores
4. Add back the exploratory session and compare

**Expected:** Tests matching the exploratory session's `risk_areas` lose the +3 bonus. Some tests may drop a tier.

<details>
<summary><strong>Worked Solution</strong></summary>

The exploratory session in `valid_input.yaml` flags `risk_areas: [RetryHandler, PaymentService]`.

Score impact of removing it (the `+3 × exploratory_match` term becomes 0):

| Test | With exploratory | Without | Tier change? |
|------|-----------------|---------|--------------|
| TEST-001 (covers PaymentService) | 14.10 | 11.10 | No — still must-run (≥8) |
| TEST-002 (covers RetryHandler) | 12.84 | 9.84 | No — still must-run (≥8) |
| TEST-003 (covers PaymentService) | 14.42 | 11.42 | No — still must-run (≥8) |

In this specific input, all tests remain above the must-run threshold even without the bonus. To see a tier change, try a scenario where a test's score sits between 5 and 8 without the bonus — the +3 would push it from should-run to must-run.

The +3 bonus models human judgement: a tester who observed real risk in an area has higher signal than the automated coverage calculation alone.

</details>

### Exercise 5: Dependency Chain Discovery

1. Create an input with Story A depending on Story B
2. Story B changes `AreaX` but Story A does not
3. Add a test covering only `AreaX`
4. Predict: does that test score > 0?
5. Run and verify

**Expected:** Yes — the test scores via `dep_coverage` because Story B (a dependency of Story A) changes `AreaX`.

<details>
<summary><strong>Worked Solution</strong></summary>

Setup:
- Story A: `risk: high`, `changed_areas: [AreaY]`, `dependency_stories: [story-b]`
- Story B: `risk: medium`, `changed_areas: [AreaX]`
- Test: `coverage_areas: [AreaX]`, `execution_time_secs: 30`, `flakiness_rate: 0.0`

Scoring:
```
direct_coverage=0  (AreaX ∉ Story A's changed_areas)             → 0
dep_coverage=1     (AreaX ∈ Story B's changed_areas)
dep_risk_mult = Story B risk_mult × 0.5 = 0.6 × 0.5 = 0.3       → 5 × 1 × 0.3 = 1.5
exploratory_match=0 (no exploratory sessions)                    → 0
flakiness_penalty (0.0)                                          → 0
raw_score = 1.5  → defer tier (<4)
```

Score is 1.5 — above zero but in the defer tier. To push this to should-run, the dependency story would need `risk: high` (dep_risk_mult = 1.0 × 0.5 = 0.5 → dep contribution = 2.5) plus an exploratory match (+3 → total = 5.5, just above the should-run threshold of 4.0).

Key insight: dependency traversal is a **signal amplifier**, not a tier guarantee. A test that only reaches a story via a low-risk dependency will correctly land in defer. High-risk dependencies give meaningful score contributions.

</details>

