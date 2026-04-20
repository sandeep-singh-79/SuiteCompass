# Usage Guide

End-to-end usage instructions for SuiteCompass — from installation to report interpretation.

---

## Prerequisites

- Python ≥ 3.13
- pip (any recent version)

---

## Installation

```bash
git clone git@github.com:sandeep-singh-79/SuiteCompass.git
cd SuiteCompass
pip install -e .
```

Verify:

```bash
iro --help
```

---

## Workflow 1: YAML-First

Write your input YAML directly and run the optimiser.

### Step 1 — Write input YAML

Create a file with three sections: `sprint_context`, `test_suite`, and `constraints`. See [V1-INPUT-TEMPLATE](V1-INPUT-TEMPLATE.md) for full schema.

### Step 2 — Run the optimiser

```bash
iro run sprint_input.yaml
```

Output prints to stdout. To write to a file:

```bash
iro run sprint_input.yaml --output report.md
```

### Step 3 — Read the report

The report contains 6 sections. See [V1-OUTPUT-TEMPLATE](V1-OUTPUT-TEMPLATE.md) for detailed interpretation.

---

## Workflow 2: Excel Import

For teams that maintain test inventories in spreadsheets.

### Step 1 — Fill the Excel template

Copy `templates/test_suite_template.xlsx` and fill in your test data. The template has 13 columns with example rows and an Instructions sheet.

Required columns: ID, Name, Layer, Coverage Areas, Execution Time (secs), Flakiness Rate.

Optional columns: Failure Count (30d), Automated, Tags, Priority, External ID, Owner, Module.

### Step 2 — Import to YAML

```bash
iro import-tests your_tests.xlsx --output test_suite.yaml
```

This produces only the `test_suite:` block:

```yaml
test_suite:
- id: TEST-001
  name: payment flow e2e
  layer: e2e
  ...
```

### Step 3 — Merge with sprint context

Create a separate file with `sprint_context` and `constraints`, then combine:

**Option A:** Manually copy the `test_suite:` block into your sprint YAML.

**Option B:** Use a YAML merge tool or script.

### Step 4 — Run the optimiser

```bash
iro run combined.yaml --output report.md
```

---

## CLI Reference

### `iro run`

```
Usage: iro run [OPTIONS] INPUT_FILE
```

Run the optimisation pipeline on INPUT_FILE and print the report.

| Option | Description |
|---|---|
| `--output, -o <path>` | Write report to file instead of stdout |

| Exit Code | Meaning |
|---|---|
| 0 | Success — report generated |
| 1 | Validation error — output contract violated (internal error) |
| 2 | Input error — file not found, parse failure, or validation failure |

### `iro benchmark`

```
Usage: iro benchmark INPUT_FILE ASSERTIONS_FILE
```

Run INPUT_FILE through the pipeline and validate the report against ASSERTIONS_FILE.

| Exit Code | Meaning |
|---|---|
| 0 | All assertions passed |
| 1 | One or more assertions failed |
| 2 | Input error — file not found or invalid |

### `iro import-tests`

```
Usage: iro import-tests [OPTIONS] XLSX_FILE
```

Import a test inventory from an Excel file and emit a `test_suite` YAML block.

| Option | Description |
|---|---|
| `--output, -o <path>` | Write YAML to file instead of stdout |
| `--sheet, -s <name>` | Sheet name to read (default: auto-detects "Tests" sheet, falls back to first sheet) |

| Exit Code | Meaning |
|---|---|
| 0 | Success — YAML generated |
| 2 | Input error — file not found, wrong format, missing columns, invalid cell values |

---

## Output Interpretation

### Optimisation Summary

The decision control panel. Key labels:

- **Sprint Risk Level** — if `high`, NFR elevation is active
- **NFR Elevation: Yes** — all perf/security tests promoted to must-run
- **Budget Overflow: Yes** — some tests were demoted from must-run because time exceeded budget
- **Total Must-Run** — tests your team must execute this sprint

### Must-Run

Tests ordered by score (highest first). Override tests show their reason in square brackets:

```
- TEST-002 retry handler integration (score: 12.8) [override: mandatory-tag:critical-flow]
```

### Should-Run If Time Permits

Second-priority tests. Run these if you have spare time after must-run completes.

### Defer To Overnight Run

Low-relevance tests. Safe to run in overnight CI — not blocking the sprint.

### Retire Candidates

Tests flagged for removal. Each shows flakiness rate and the "no unique coverage" notation:

```
- TEST-099 legacy check (flakiness: 0.42, no unique coverage)
```

Before retiring: confirm with the team that no unique business logic depends on these tests.

### Suite Health Summary

Top-level health indicators for your entire suite, not just this sprint's selection.

---

## Benchmark Workflow

Validate that the optimiser produces correct output for a known scenario:

```bash
iro benchmark benchmarks/high-risk-feature-sprint.input.yaml \
              benchmarks/high-risk-feature-sprint.assertions.yaml
```

Expected output on pass:

```
OK — 18 checks passed.
```

On failure:

```
FAIL — assertion errors:
  - must_include_substrings: expected "TEST-003" in output
```

See [VALIDATION-HARNESS](VALIDATION-HARNESS.md) for how to add new benchmark scenarios.

---

## Adding a New Benchmark

1. Create `benchmarks/<scenario-name>.input.yaml` — a valid SuiteCompass input
2. Run: `iro run benchmarks/<scenario-name>.input.yaml` — inspect the output
3. Create `benchmarks/<scenario-name>.assertions.yaml` — define expected headings, labels, substrings
4. Verify: `iro benchmark benchmarks/<scenario-name>.input.yaml benchmarks/<scenario-name>.assertions.yaml`

---

## Error Handling

| Situation | Exit Code | Message |
|---|---|---|
| File not found | 2 | `Error: File not found: 'path'` |
| Invalid YAML syntax | 2 | `Error: YAML parse error: ...` |
| Missing required field | 2 | `Error: Missing required field: ...` |
| Invalid field value | 2 | `Error: Field 'risk' must be one of: ...` |
| Excel: wrong file format | 2 | `Error: Unsupported file format: '.csv'. Use .xlsx format.` |
| Excel: missing column | 2 | `Error: Missing required column(s): ['ID']...` |
| Excel: invalid cell value | 2 | `Error: Row 3, column 'Flakiness Rate': value 1.5 must be between 0.0 and 1.0` |
| Excel: merged cells | 2 | `Error: Merged cells detected in sheet 'Tests': B2:C2...` |
| Output contract violated | 1 | `Validation error: Missing heading: ## Retire Candidates` |

---

## Current Limitations

- **No LLM layer** — all output is formula-driven; no narrative or explanation generation
- **No fuzzy area matching** — `coverage_areas` matched by exact string equality
- **1-hop dependencies only** — transitive dependency chains not followed
- **No multi-sprint history** — operates on a single sprint snapshot
- **No SCM integration** — `changed_areas` must be provided manually
- **No Jira/TestRail connector** — sprint context must be written by hand or imported via Excel
- **Story `type` not scored** — carried in input for future use only
