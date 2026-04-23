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
    │            flaky + unique coverage → Flaky-Critical
    ▼
5. Warnings ── inspect final tier state and emit advisory signals:
    │           COVERAGE-GAP, NO-MUST-RUN-COVERAGE, FLAKINESS-REVERSED,
    │           OVERRIDE-BUDGET, UNIQUE-DEMOTED, ZERO-BUDGET, NFR-NO-OVERLAP
    ▼
6. Rendering ── Markdown report with 8 sections:
               Optimisation Summary, Must-Run, Should-Run, Defer,
               Retire Candidates, Flaky Critical Coverage,
               Suite Health Summary, Warnings
```

**What this means in practice:**
- A test with no coverage overlap to any changed story will score near zero and land in Defer — correctly.
- A test covering a high-risk story scores 3.3× higher than the same test covering a low-risk story.
- NFR elevation bypasses scoring entirely — performance and security tests run unconditionally when sprint risk is high.
- Budget overflow trims from the bottom of must-run, never from overrides.
- Warnings surface silent decisions — e.g. a high-risk story with no must-run coverage, or a test whose flakiness pushed it below the must-run threshold. Warnings are advisory: they do not change tier assignments.

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

## 5. Interpreting the Flaky Critical Coverage Section

The `## Flaky Critical Coverage` section appears whenever at least one test is both highly flaky **and** the only test that covers some sprint-relevant area. It is one of the most important signals SuiteCompass emits, because it represents a risk the scoring formula alone cannot resolve.

### What it means

A test in this section:
- Has `flakiness_rate > flakiness_high_tier_threshold` (default 0.20) — it fails spuriously often enough to erode developer trust
- Covers a story area that is being changed this sprint (`coverage_areas ∩ story.changed_areas`)
- Covers that area **uniquely** — no other test in the suite watches the same code path

The scoring formula has already penalised this test's score (−8 × flakiness_rate). Without the flaky-critical classification, it might land in Defer or Should-Run and be skipped under budget pressure — leaving its unique area completely unchecked.

### The unique coverage gate

The key criterion is **unique coverage**. A flaky test that covers areas also covered by other (stable) tests is handled differently:

| Unique coverage? | Result |
|---|---|
| Yes | Flaky-critical — must run, report signals invest/replace |
| No | Retire candidate — safe to remove, other tests cover the area |

This is why the same flakiness threshold can produce two completely different outcomes depending on whether other tests provide safety cover.

### Execution policy

- **Always run** — budget-exempt, never demoted by budget overflow, treated like a hard override
- **Rerun on failure** — the report recommends rerunning up to `flaky_critical_rerun_max` times (default 2) before treating a failure as confirmed
- **Does not gate the release** — a flaky-critical failure is a signal, not a hard block; the team decides

### The `stabilize or replace` action

Every flaky-critical test gets a `stabilize or replace` annotation. This is not a severity label — it is a team action prompt. Two valid responses:

1. **Stabilize** — fix the root cause of the flakiness (timing issues, environment coupling, brittle assertions)
2. **Replace** — write a new stable test covering the same area, then retire the flaky one

Leaving a test in the flaky-critical list sprint after sprint is a warning sign: the team is acknowledging risk without addressing it.

### Contrast with Retire Candidates

| Aspect | Flaky-Critical | Retire Candidate |
|---|---|---|
| Unique coverage | Yes | No |
| Must run | Yes (always) | No (remove) |
| Budget impact | Exempt | N/A |
| Team action | Stabilize or replace | Archive/delete |
| Appears in scored tiers | No | No |

---

## 6. Common Mistakes in Regression Prioritisation

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

## 6. How to Read an LLM-Enhanced Report

SuiteCompass can run in `--mode llm` or `--mode compare` to add prose explanations to the deterministic output. This section explains what changes, what stays the same, and how to trust the result.

### What the LLM Adds

The LLM does not change scores, tiers, or tier assignments. The deterministic pipeline runs first — every test is scored, tiered, and checked against the budget exactly as in `--mode deterministic`. The LLM receives the full scoring context (sprint risks, changed areas, tier lists, health metrics) and explains the decisions in plain language.

Think of it as an analyst who receives a spreadsheet of scores and writes a brief explaining why the numbers came out the way they did. The spreadsheet is authoritative; the analyst's brief summarises it for a wider audience.

### Why Scores Are Still Authoritative

The LLM operates after the scoring engine, not before. It cannot demote a must-run test, promote a deferred test, or remove a retire candidate. If the LLM output contradicts the deterministic scores it is because the LLM hallucinated content — and the structural repair or fallback mechanisms will correct or override that content.

**The rule:** if you want to understand why a test is in must-run, check its score in the report. The prose narrative is a reading aid, not a decision record.

### The Three Recommendation Modes

Every LLM-mode report carries a `Recommendation Mode:` label that tells you which path was taken:

| Label value | What happened |
|---|---|
| `Recommendation Mode: llm` | LLM output passed all structural checks; used as-is |
| `Recommendation Mode: llm-repaired` | LLM output had missing headings or labels; repaired automatically before use |
| `Recommendation Mode: deterministic-fallback` | LLM failed completely (exception, timeout, bad output that could not be repaired); deterministic report used |

All three paths produce a structurally valid report and exit with code 0. You can run LLM mode in CI without worrying about a provider outage breaking your pipeline — the worst case is a clean deterministic fallback.

### How Fallback Works

The fallback chain runs automatically, with no intervention needed:

```
1. LLM generate()
   │
   ├─ Exception (network, auth, timeout)
   │     → Recommendation Mode: deterministic-fallback (exit 0)
   │
   └─ Output received
         │
         ├─ Passes validation → Recommendation Mode: llm
         │
         └─ Fails validation
               │
               ├─ Repair succeeds → Recommendation Mode: llm-repaired
               │
               └─ Repair fails → Recommendation Mode: deterministic-fallback
```

Every path through the chain produces a valid report and exits 0. Provider exceptions are treated as recoverable: the engine falls back to deterministic output so CI never breaks due to an LLM outage.

### Using Compare Mode

`--mode compare` runs both pipelines in one command and delivers a side-by-side view. This is useful for:

- Evaluating how well a new model or prompt explains a specific scenario
- Auditing whether LLM narrative content is consistent with the deterministic scores
- QA teams who want both the structured recommendation and the prose justification

The comparison output includes a `## Comparison Summary` block showing the LLM mode and repair count, followed by both report bodies.

### When to Use Each Mode

| Situation | Recommended mode |
|---|---|
| CI pipeline, audit log, repeatable output | `deterministic` |
| Stand-up or executive review with narrative context | `llm` |
| Evaluating or testing a new LLM provider or model | `compare` |
| Regulated environment where all inputs/outputs must be deterministic | `deterministic` |

LLM mode adds value when the output goes to a human reader who benefits from explanation. In automated pipelines that parse the report or feed it to downstream tools, `deterministic` is the right default.

---

## 7. How CI History Improves Flakiness Accuracy

### The Problem With YAML Flakiness

When engineers declare `flakiness_rate: 0.05` in the input YAML, they are making an estimate. This estimate is typically stale (written at suite creation time), optimistic (nobody wants to admit their tests are flaky), or undiscovered (a test only started flaking after an infrastructure change last Tuesday). YAML-declared flakiness is a useful starting point, but it diverges from reality over time.

### What the History Layer Adds

SuiteCompass supports a second flakiness signal: actual CI execution history loaded from JUnit XML reports. When `--history-dir` or `--history-file` is supplied, the system overlays the observed failure rate onto each test's metadata before scoring begins.

The merge rule is straightforward:
- If a test has no CI history entry, the YAML flakiness is used unchanged.
- If a test has a CI history entry, **the history-derived flakiness replaces the YAML flakiness** entirely. The YAML value is discarded.
- If the history flakiness is materially different from the YAML flakiness, a `[history-override]` warning is emitted, naming the test and both values.

This makes it possible to have a YAML that says `flakiness_rate: 0.02` (author was optimistic) but have the actual run use `0.76` derived from 200 CI builds.

### When History Changes Tier Assignment

Flakiness affects scoring via the retire threshold:

- Tests at or above `flakiness_retire_threshold` (default `0.30`) are placed in the **Retire Candidates** tier regardless of coverage score.
- Tests above `flakiness_high_tier_threshold` (default `0.20`) receive a score penalty that can push them down from must-run to should-run.

If YAML says `flakiness_rate: 0.05` but history says `0.85`, the test will be moved to **Retire Candidates** by the history overlay — without any changes to the input YAML. The warning signals this invisible tier shift:

```
[history-override] TestName: yaml=0.05, history=0.85
```

Reading warnings is important. A high retire count combined with `[history-override]` warnings signals that your YAML is out of sync with reality.

### When YAML and History Disagree: Trust the History, Flag the Drift

History always wins. The `[history-override]` warning is not a conflict to resolve — it is a data quality signal. The right response is to:
1. Confirm the history data covers enough runs to be reliable (aim for ≥30 recent builds).
2. Update the YAML flakiness value to match history if you want the YAML to be authoritative again.
3. If the discrepancy is intentional (e.g., a known transient flakiness spike), use `--history-file` with a pre-computed average over a longer window.

### `--history-dir` vs `--history-file`

| Flag | Use When |
|---|---|
| `--history-dir <path>` | You have raw JUnit XML files (e.g., from CI artifact storage). The system parses them and computes per-test stats. |
| `--history-file <path>` | You have a pre-computed YAML mapping `test_id: {failure_count, run_count}`. Useful for sharing computed history across teams or time windows. |

In CI pipelines, `--history-dir` is the natural choice: point it at the artifact folder for the last N builds. In cross-team or regulatory contexts, `--history-file` lets you commit a stable, reviewed history snapshot.

### How Git Diff Area Mapping Works

The `iro diff-areas` command reads a `--area-map` file that maps file glob patterns to area labels:

```yaml
# area-map.yaml
areas:
  - label: PaymentService
    patterns: ["src/payments/**", "lib/card_processing/**"]
  - label: NotificationService
    patterns: ["src/notifications/**"]
```

When `iro diff-areas --area-map area-map.yaml --ref HEAD~1` is run, it:
1. Lists all changed files in the diff.
2. Matches each changed file against every area's glob patterns.
3. Emits the set of area labels that had at least one matching file.

You then pass this output to `iro run --area-map area-map.yaml`, which replaces the `changed_areas` in each sprint story with the areas derived from the diff. This removes the manual step of declaring which areas changed — the commit history drives it automatically.

The conceptual benefit: test selection becomes a function of what actually changed in the codebase, not what an engineer remembered to declare in the sprint YAML. In a mature pipeline, `iro diff-areas` and `iro run --area-map` run back-to-back in CI, and the sprint YAML only needs stories, constraints, and dependency definitions.

---

## 8. Hands-On Exercises

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

### Exercise 6: History Override and Tier Shift

This exercise reinforces how CI history silently overrides YAML flakiness and moves a healthy-looking test to the Retire Candidates tier.

1. Create an input YAML with one test: `id: T1`, `flakiness_rate: 0.02`, `coverage_areas: [AreaA]`, `execution_time_secs: 30`
2. Add a story with `risk: high`, `changed_areas: [AreaA]`
3. Run `iro run` — predict which tier T1 lands in (hint: flakiness is below the retire threshold).
4. Create a history YAML file:
   ```yaml
   T1:
     failure_count: 75
     run_count: 100
   ```
5. Run `iro run --history-file <path>` — predict the tier change before running.
6. Verify: T1 should appear in **Retire Candidates** and the output should contain a `[history-override]` warning.

**Expected:** T1 scores well in step 3 (direct coverage with high-risk story, low flakiness → must-run or should-run). In step 6, history flakiness of 0.75 exceeds the retire threshold, so T1 is retired. Warning: `[history-override] T1: yaml=0.02, history=0.75`.

<details>
<summary><strong>Key Insight</strong></summary>

The YAML `flakiness_rate: 0.02` is never consulted once a history entry exists. The history-derived rate (75/100 = 0.75) replaces it entirely. This is intentional — observed CI data is more reliable than declared estimates.

The `[history-override]` warning exists precisely to surface this kind of YAML drift. A 0.02 → 0.75 discrepancy usually indicates the test started flaking after the YAML was written. Action: investigate the root cause, fix or retire the test, then update the YAML if you keep it.

</details>

### Exercise 7: Diff-Derived Area Mapping

This exercise demonstrates how `iro diff-areas` removes the need to manually declare `changed_areas` in the sprint YAML.

1. Create a sprint YAML with one story: `risk: high`, `changed_areas: [ServiceA]`
2. Add two tests: one covering `ServiceA`, one covering `ServiceB`
3. Run `iro run` normally — confirm the ServiceA test scores and the ServiceB test does not.
4. Create an area map file:
   ```yaml
   areas:
     - label: ServiceB
       patterns: ["src/service_b/**"]
     - label: ServiceA
       patterns: ["src/service_a/**"]
   ```
5. Run `iro diff-areas --area-map area-map.yaml --ref HEAD~1` — inspect the output. It will list the areas that match changed files at HEAD~1.
6. Run `iro run --area-map area-map.yaml` — this replaces the story's `changed_areas` with the diff-derived set.
7. Predict: if the diff included files in `src/service_b/`, the ServiceB test should now appear in a higher tier.

**Expected:** The area map drive the test selection automatically. Tests whose coverage areas match diff-touched areas are promoted. Tests whose areas were not changed are scored at zero unless they have a dependency path.

<details>
<summary><strong>When to Use This Pattern</strong></summary>

The diff-area pattern is most valuable in two scenarios:

1. **Large monorepos** where sprint stories accumulate stale `changed_areas` declarations. Developers forget to update them. The diff map makes declarations automatic.
2. **CI regression gates** where you want test selection to be 100% reproducible from the commit graph, not from human memory.

For small teams with disciplined YAML hygiene, the manual `changed_areas` approach is simpler and works fine. The diff map is the next evolution once maintaining declarations becomes a bottleneck.

</details>

