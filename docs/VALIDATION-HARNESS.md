# Validation Harness

How the SuiteCompass benchmark system works, how to run it, and how to add new scenarios.

---

## Validation Philosophy

All validation in SuiteCompass is **binary pass/fail**. There are no subjective quality scores, no weighted metrics, no "partial passes." A check either passes or it fails.

This applies at three layers:

1. **Input validation** — rejects invalid input before processing
2. **Output structure validation** — ensures the rendered report meets the contract
3. **Benchmark assertions** — verifies correctness for known scenarios

---

## Layer 1: Input Validation

Performed by `input_loader.py` during every `iro run` invocation.

**Checks:**
- YAML parseable
- Three top-level keys present (`sprint_context`, `test_suite`, `constraints`)
- All required fields present with correct types
- Risk values in allowed set (`high`, `medium`, `low`)
- Layer values in allowed set (`e2e`, `integration`, `unit`, `security`, `performance`)
- `flakiness_rate` within 0.0–1.0
- `execution_time_secs` ≥ 0
- `dependency_stories` IDs reference existing stories
- Lists are actually lists (not strings or scalars)

**On failure:** exit code 2 with descriptive error message.

---

## Layer 2: Output Structure Validation

Performed by `output_validator.py` after report rendering. Runs automatically inside `iro run`.

**Checks:**
- All **8** required headings present (line-anchored)
- All 8 required labels present exactly once
- No label duplicated
- Each label in its declared section

**On failure:** exit code 1 (validation error). This indicates an internal bug — the renderer produced invalid output.

---

## Layer 3: Benchmark Assertions

Performed via `iro benchmark <input.yaml> <assertions.yaml>`. Used during development and CI to verify correctness for known scenarios.

### Assertion File Schema

Assertion files are YAML with four optional top-level keys:

```yaml
# All checks are binary pass/fail against the rendered markdown report.

must_include_headings:
  - "## Optimisation Summary"
  - "## Must-Run"
  # ... (list of headings that must appear as line-anchored)

must_include_labels:
  - "Recommendation Mode:"
  - "Sprint Risk Level:"
  # ... (list of label prefixes that must appear)

must_include_substrings:
  - "NFR Elevation: Yes"
  - "TEST-003"
  # ... (list of substrings that must appear anywhere in the output)

must_not_include_substrings:
  - "TEST-007 legacy smoke manual (flakiness:"
  # ... (list of substrings that must NOT appear)
```

### Assertion Types

| Key | Check |
|---|---|
| `must_include_headings` | Each heading appears as an exact line (line-anchored) |
| `must_include_labels` | Each label appears as a line prefix somewhere in output |
| `must_include_substrings` | Each string appears somewhere in the rendered markdown |
| `must_not_include_substrings` | Each string does NOT appear anywhere in the rendered markdown |

### Assertion Execution

Each entry in each list is one check. The benchmark runner counts total checks and reports all failures:

```
OK — 18 checks passed.
```

or:

```
FAIL — assertion errors:
  - must_include_substrings: expected "TEST-003" in output
  - must_not_include_substrings: found "TEST-007 legacy smoke..." in output
```

---

## Running Benchmarks

### Run a single benchmark

```bash
iro benchmark benchmarks/high-risk-feature-sprint.input.yaml \
              benchmarks/high-risk-feature-sprint.assertions.yaml
```

### Run all benchmarks

```bash
for f in benchmarks/*.input.yaml; do
  assertions="${f%.input.yaml}.assertions.yaml"
  echo "=== $f ==="
  iro benchmark "$f" "$assertions"
done
```

Or as part of the test suite:

```bash
pytest tests/test_benchmark_runner.py
```

---

## Current Benchmark Set

| Scenario | Input File | Assertions File | Key Checks |
|---|---|---|---|
| High-Risk Feature Sprint | `high-risk-feature-sprint.input.yaml` | `high-risk-feature-sprint.assertions.yaml` | NFR elevation active, perf/security in must-run, budget overflow, manual test handling |
| Low-Risk Bugfix Sprint | `low-risk-bugfix-sprint.input.yaml` | `low-risk-bugfix-sprint.assertions.yaml` | Low sprint risk, minimal must-run, no retire candidates, no NFR elevation |
| Degraded Suite / High Flakiness | `degraded-suite-high-flakiness.input.yaml` | `degraded-suite-high-flakiness.assertions.yaml` | Retire candidates identified, flakiness tier high count, suite health degraded |
| Flaky-Critical Sprint | `flaky-critical-sprint.input.yaml` | `flaky-critical-sprint.assertions.yaml` | Flaky-critical elevation, unique coverage protection, retire vs FC split |
| Stressed Sprint / Coverage Gaps | `stressed-sprint-coverage-gaps.input.yaml` | `stressed-sprint-coverage-gaps.assertions.yaml` | 5 warning types fired: COVERAGE-GAP, OVERRIDE-BUDGET, NO-MUST-RUN-COVERAGE, NFR-NO-OVERLAP, FLAKINESS-REVERSED |

Additionally, `benchmarks/sample-import.xlsx` is used for Excel import round-trip testing.

---

## Adding a New Benchmark

### Step 1 — Design the scenario

Identify what behaviour you want to verify. Refer to the [Scenario Library](SCENARIO-LIBRARY.md) for inspiration.

### Step 2 — Create the input file

```bash
# Create benchmarks/<scenario-name>.input.yaml
```

Ensure it passes input validation:

```bash
iro run benchmarks/<scenario-name>.input.yaml
```

### Step 3 — Inspect the output

Review the report to understand what the optimizer produces for your scenario. Note:
- Which tests are in which tier
- Whether NFR elevation is active
- Whether budget overflow occurred
- Any retire candidates

### Step 4 — Write assertions

Create `benchmarks/<scenario-name>.assertions.yaml`:

```yaml
must_include_headings:
  - "## Optimisation Summary"
  - "## Must-Run"
  - "## Flaky Critical Coverage"
  - "## Should-Run If Time Permits"
  - "## Defer To Overnight Run"
  - "## Retire Candidates"
  - "## Suite Health Summary"
  - "## Warnings"

must_include_labels:
  - "Recommendation Mode:"
  - "Sprint Risk Level:"
  - "Total Must-Run:"

must_include_substrings:
  # Add specific expected values and test IDs
  - "Sprint Risk Level: high"  # or medium/low
  - "TEST-001"                 # specific test expected in output

must_not_include_substrings:
  # Add things that should NOT appear
  - "some_forbidden_text"
```

### Step 5 — Verify

```bash
iro benchmark benchmarks/<scenario-name>.input.yaml \
              benchmarks/<scenario-name>.assertions.yaml
```

Expected: `OK — N checks passed.`

### Step 6 — Commit

Add both files to version control. The CI pipeline will run all benchmarks on every push.

---

## Best Practices for Assertions

1. **Always include all 8 headings** — catches rendering regressions
2. **Assert specific test IDs** in expected tiers — catches scoring regressions
3. **Assert label values** (e.g. `Sprint Risk Level: high`) not just label presence
4. **Use `must_not_include_substrings`** for negative assertions — e.g. manual tests should never appear in retire format
5. **Keep assertions independent** — each benchmark should test one scenario's behaviour
6. **Name scenarios descriptively** — the filename should indicate what's being tested
