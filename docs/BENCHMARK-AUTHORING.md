# Benchmark Authoring Guide

How to write, structure, and validate a SuiteCompass benchmark. A benchmark is a pair of files: an **input file** describing a sprint scenario and a **assertions file** defining what the output must contain. Together they create a repeatable, binary-pass/fail regression test for the scoring pipeline.

---

## When to Write a Benchmark

Write a benchmark when you want to:
- Prove a specific scoring behaviour (e.g. "NFR elevation fires on high-risk sprints")
- Lock in a regression test for a newly discovered edge case
- Demonstrate a named scenario for teaching purposes
- Validate a scoring formula change doesn't break known-good behaviour

A benchmark is not a unit test. It tests the full pipeline end-to-end (input → classify → score → render → assert).

---

## File Naming Convention

```
benchmarks/<scenario-slug>.input.yaml
benchmarks/<scenario-slug>.assertions.yaml
```

Use a descriptive slug: `high-risk-feature-sprint`, `degraded-suite-high-flakiness`, `budget-overflow-demotion`. The slug becomes the benchmark name in `iro benchmark` output.

---

## Part 1 — The Input File

The input file is a valid SuiteCompass YAML input. Follow the schema from [V1-INPUT-TEMPLATE](V1-INPUT-TEMPLATE.md).

### Structure

```yaml
# Benchmark: <scenario-slug>
# One-line description of what this scenario tests.
# Expected: <key properties of the expected output>

sprint_context:
  sprint_id: <unique ID>
  stories:
    - id: <STORY-ID>
      title: <human label>
      risk: high | medium | low
      type: feature | bugfix | refactor | ...
      changed_areas:
        - AreaName
      dependency_stories:
        - STORY-ID   # or [] if none
  exploratory_sessions:   # or [] if none
    - session_id: <EX-ID>
      tester: <name>
      risk_areas:
        - AreaName

test_suite:
  - id: TEST-NNN
    name: <human label>
    layer: unit | integration | e2e | performance | security
    coverage_areas: [AreaName]
    execution_time_secs: <number>
    flakiness_rate: <0.00–1.00>
    failure_count_last_30d: <integer>   # optional, defaults to 0
    automated: true | false             # optional, defaults to true
    tags: [tag-name]                    # optional

constraints:
  time_budget_mins: <integer>
  mandatory_tags: [tag-name]           # or []
  flakiness_retire_threshold: 0.30
  flakiness_high_tier_threshold: 0.20
```

### Design Principles

**1. Each test should have a clear purpose in the scenario.**  
Every test should be there to prove something. If you can remove a test without changing any assertion, remove it. Minimal inputs are easier to reason about.

**2. Use IDs and area names consistently.**  
`changed_areas` in stories and `coverage_areas` in tests must share the same strings for overlap detection. `PaymentService` ≠ `payment_service`. Keep a mental map: what areas exist in this scenario, what tests cover them.

**3. Design at least one test per interesting tier.**  
A good benchmark proves that the scoring draws the right distinctions. Include tests that should land in must-run, should-run, and defer — not just must-run. Edge cases at tier boundaries (score ≈ 8.0 or ≈ 4.0) are especially valuable.

**4. Make the header comment work as documentation.**  
The `# Benchmark:` and `# Expected:` comments are read by humans, not the tool. Write them clearly — they are the benchmark's test intent.

---

## Part 2 — The Assertions File

The assertions file defines what the rendered Markdown output must contain. The runner checks all four assertion types and reports each failure independently.

### Structure

```yaml
# Assertions for: <scenario-slug>
# (optional extra comment explaining what this set proves)

must_include_headings:
  - "## Optimisation Summary"     # exact heading text, line-anchored

must_include_labels:
  - "Sprint Risk Level:"          # label substring present anywhere in output

must_include_substrings:
  - "NFR Elevation: Yes"          # any substring anywhere in output

must_not_include_substrings:
  - "TEST-007 legacy smoke manual (flakiness:"   # must NOT appear
```

### The Four Assertion Types

**`must_include_headings`**  
Matched line-by-line with `line.rstrip() == heading`. Use the exact heading text including `##` prefix. Every benchmark should include all six standard headings to confirm the report structure is intact.

Standard set (copy into every benchmark):
```yaml
must_include_headings:
  - "## Optimisation Summary"
  - "## Must-Run"
  - "## Should-Run If Time Permits"
  - "## Defer To Overnight Run"
  - "## Retire Candidates"
  - "## Suite Health Summary"
```

**`must_include_labels`**  
Substring match anywhere in the output. Use for required summary labels in the Optimisation Summary block. Labels confirm the report emits the field even if you don't assert the specific value.

Standard set:
```yaml
must_include_labels:
  - "Recommendation Mode:"
  - "Sprint Risk Level:"
  - "Total Must-Run:"
  - "Total Retire Candidates:"
  - "NFR Elevation:"
  - "Budget Overflow:"
  - "Flakiness Tier High:"
```

**`must_include_substrings`**  
Assert specific property values and test IDs. This is where the scenario's intent is expressed.

Examples:
```yaml
must_include_substrings:
  - "Sprint Risk Level: high"        # assert the derived sprint risk
  - "NFR Elevation: Yes"             # assert NFR elevation fired
  - "Budget Overflow: No"            # assert budget was not exceeded
  - "TEST-003"                       # assert a specific test is in the output
  - "[override: nfr-elevation]"      # assert override reason rendered
  - "(manual)"                       # assert a manual test is marked
```

**`must_not_include_substrings`**  
Assert things that must NOT be in the output. Use sparingly but it is the only way to assert a test is NOT in a section, or that a specific error doesn't appear.

```yaml
must_not_include_substrings:
  # Manual tests must never be retire candidates
  - "TEST-007 legacy smoke manual (flakiness:"
  # A test with unique coverage must not be retired
  - "TEST-206 flaky inventory unique check (flakiness:"
```

### What Not to Assert

- Don't assert exact scores (e.g. `"score: 9.84"`) — they change when formula constants are tuned.
- Don't assert section membership with substring alone (e.g. asserting `TEST-001` is in must-run vs. should-run requires the test ID to appear with context — use `must_not_include_substrings` to exclude wrong placements instead).
- Don't duplicate the standard headings/labels boilerplate in every explanation; just include them.

---

## Running a Benchmark

```bash
# Run with assertions (binary pass/fail)
iro benchmark benchmarks/my-scenario.input.yaml \
              benchmarks/my-scenario.assertions.yaml

# Run without assertions (inspect output manually before writing assertions)
iro run benchmarks/my-scenario.input.yaml
```

**Workflow for authoring:**
1. Write the input file
2. Run `iro run <input>` and read the output
3. Verify the output matches your intent
4. Write the assertions file based on the actual output
5. Run `iro benchmark <input> <assertions>` — must pass
6. Commit both files together

---

## Worked Example — Budget Overflow Scenario

**Goal:** prove that scored must-run tests are demoted when total execution time exceeds budget, but override tests survive demotion.

**Input design:**
- 1 high-risk story: `risk: high`, `changed_areas: [CheckoutService]`
- 4 tests covering `CheckoutService`, `execution_time_secs: 600` each (10 min each)
- 1 security test (NFR override, budget-exempt)
- `time_budget_mins: 15` (budget fits only 1–2 scored tests)

**Expected output:**
- Security test in Must-Run (`[override: nfr-elevation]`)
- 1–2 highest-scored tests in Must-Run (within 15-min budget minus security test time)
- Remaining scored tests demoted to Should-Run
- `Budget Overflow: Yes`

**Assertions:**
```yaml
must_include_substrings:
  - "Sprint Risk Level: high"
  - "NFR Elevation: Yes"
  - "Budget Overflow: Yes"
  - "[override: nfr-elevation]"
  - "TEST-SECURITY-01"           # override test always present
```

---

## Checklist Before Committing

- [ ] Input passes `iro run` without validation errors
- [ ] Every test in the input has a clear role — remove any that don't affect assertions
- [ ] Header comment accurately describes the scenario and expected key properties
- [ ] Assertions file includes the standard headings and labels boilerplate
- [ ] `must_include_substrings` proves the scenario's core behaviour (not just that tests exist)
- [ ] `must_not_include_substrings` used for any exclusion requirements (manual tests, unique-coverage tests)
- [ ] `iro benchmark <input> <assertions>` reports `OK — N checks passed`
- [ ] Both files committed together with a clear name matching the scenario slug
