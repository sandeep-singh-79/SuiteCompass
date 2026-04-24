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

## Workflow 0: Quick Start from Template

Generate a pre-structured input YAML instead of writing one from scratch.

### Plain scaffold

```bash
iro init -o my-sprint.yaml
```

Opens `my-sprint.yaml` with all required sections (`sprint_context`, `test_suite`, `constraints`) and inline `# TODO` comments guiding each field.  Fill in the TODOs, then proceed to Workflow 1.

### Pre-populate from JUnit XML history

If you have a directory of JUnit XML files from previous CI runs, SuiteCompass can extract test IDs, names, average execution times, and flakiness rates automatically:

```bash
iro init --from-junit path/to/junit-xml-dir/ -o my-sprint.yaml
```

The generated file will have one test entry per discovered test, with `layer` and `coverage_areas` left as `TODO` placeholders.  Fill those in, add `sprint_context`, and run.

### Options

| Flag | Description |
|---|---|
| `--output, -o <path>` | Write template to file (default: print to stdout) |
| `--from-junit <dir>` | Pre-populate test entries from JUnit XML history directory |

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

The report contains 8 sections. See [V1-OUTPUT-TEMPLATE](V1-OUTPUT-TEMPLATE.md) for detailed interpretation.

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

Create a separate `sprint.yaml` file with `sprint_context` and `constraints` (see [V1-INPUT-TEMPLATE](V1-INPUT-TEMPLATE.md) for schema).

Then run with the split-file flags — no manual merge required:

```bash
iro run --tests test_suite.yaml --sprint sprint.yaml --output report.md
```

Alternatively, if you prefer a single combined file:

**Option B (manual):** Copy the `test_suite:` block from `test_suite.yaml` into your sprint YAML and run:

```bash
iro run combined.yaml --output report.md
```

### Step 4 — Run the optimiser

With split-file mode (recommended):

```bash
iro run --tests test_suite.yaml --sprint sprint.yaml
```

With a combined file:

```bash
iro run combined.yaml --output report.md
```

---

## Workflow 3: Split-File Mode

For teams that keep test inventories and sprint context in separate files permanently. No merging required.

### When to use

- You use `iro import-tests` to produce `test_suite.yaml` from Excel
- Your sprint context lives in a separate `sprint.yaml` file
- You don't want to maintain a combined file

### How it works

```bash
# Step 1 — Import tests from Excel (or maintain test_suite.yaml manually)
iro import-tests tests.xlsx --output test_suite.yaml

# Step 2 — Maintain sprint_context + constraints in a sprint file
# sprint.yaml contains: sprint_context, constraints (NOT test_suite)

# Step 3 — Run using both files
iro run --tests test_suite.yaml --sprint sprint.yaml
```

### sprint.yaml structure for split-file mode

```yaml
sprint_context:
  sprint_id: SPRINT-42
  stories:
    - id: PROJ-1100
      title: Add retry logic
      risk: high
      type: feature
      changed_areas:
        - PaymentService
      dependency_stories: []
  exploratory_sessions: []

constraints:
  time_budget_mins: 20
  mandatory_tags:
    - critical-flow
  flakiness_retire_threshold: 0.30
  flakiness_high_tier_threshold: 0.20
```

Note: `sprint.yaml` must contain `sprint_context` and `constraints` but does **not** contain `test_suite`.

### Validation rules for split-file mode

- `--tests` and `--sprint` must always be used together
- `--tests` file must contain a `test_suite` key
- `--sprint` file must contain both `sprint_context` and `constraints` keys
- Cannot combine `INPUT_FILE` argument with `--tests`/`--sprint` flags
- Full schema validation (required fields, types, value ranges) applies to the merged data

---

## Workflow 4: CI History Overlay

Augment the optimiser's flakiness scoring with real test history from your CI system.

### Step 1 — Collect JUnit XML reports

Point `--history-dir` at a folder of JUnit XML files (one file per CI run):

```bash
iro run input.yaml --history-dir ./ci-reports/
```

Or supply a pre-computed CSV/JSON file:

```bash
iro run input.yaml --history-file ./flakiness.csv
```

### History file formats

**CSV** (`.csv`):

```csv
test_id,flakiness_rate,failure_count_last_30d,total_runs
TEST-001,0.12,3,25
TEST-002,0.05,1,20
```

**JSON** (`.json`) — map of `test_id → record`:

```json
{
  "TEST-001": {"flakiness_rate": 0.12, "failure_count_last_30d": 3, "total_runs": 25}
}
```

When a test ID in history matches a test in the input, `flakiness_rate` is overridden with the history value and `failure_count_last_30d` / `total_runs` are added. Tests absent from history are left unchanged.

---

## Workflow 5: Git Diff → Area Mapping

Automatically derive `changed_areas` from a git diff instead of writing them by hand.

### When to use

- You have a YAML input where `changed_areas` reflects what the diff changed — not what was planned
- Your team commits to a `main`/`develop` branch and wants CI to derive areas automatically

### Step 1 — Create area-map.yaml

Copy `templates/area-map.yaml` and edit it to match your project layout:

```yaml
mappings:
  - pattern: "src/payments/**"
    areas:
      - Payments
  - pattern: "src/checkout/**"
    areas:
      - Checkout
      - Payments
  - pattern: "tests/**"
    areas: []        # test-only changes add no coverage areas
```

Each `pattern` is a glob matched via `fnmatch` — `**` crosses directory boundaries. A file may match multiple patterns; all matching `areas` are unioned.

### Step 2 — Preview the derived areas

```bash
# From a diff file (git diff --name-only output)
git diff --name-only HEAD~1 > changed-files.txt
iro diff-areas --area-map area-map.yaml --diff-file changed-files.txt

# Or directly from a git ref
iro diff-areas --area-map area-map.yaml --ref HEAD~1
```

Output (YAML fragment, paste into sprint_context.stories):

```yaml
changed_areas:
- Checkout
- Payments
```

### Step 3 — Run with area-map override

```bash
# Override changed_areas in the input using git diff
iro run input.yaml --area-map area-map.yaml --ref HEAD~1

# Or from a saved diff file
iro run input.yaml --area-map area-map.yaml --diff-file changed-files.txt
```

The `--area-map` flag replaces `changed_areas` on **every story** in the input with the set derived from the diff. This is intended for single-story or single-PR workflows where one diff maps cleanly to the sprint scope.

### Rules

- `--area-map` requires exactly one of `--diff-file` or `--ref` (mutually exclusive)
- `--diff-file` must point to an existing file
- `--ref` is passed directly to `git diff --name-only <ref>`. This option is required when `--diff-file` is not provided.
- The tool must be run from within the repository root (or any sub-directory) for `--ref` to work

---

## Workflow 6: LLM-Enhanced Report

Generate a prose-enhanced report using an LLM provider. The deterministic scores and tier assignments remain unchanged — the LLM adds narrative explanations, not decisions. The output always satisfies the same structural contract regardless of which provider path is taken.

### Prerequisites

**Ollama (recommended for local/offline use):**

```bash
# Install and start Ollama — https://ollama.com
ollama serve
ollama pull llama3
```

**OpenAI:**

```bash
export IRO_LLM_API_KEY=sk-...
```

**Gemini:**

```bash
export IRO_LLM_API_KEY=AIza...
```

### Step 1 — Run in LLM mode

```bash
# Ollama (local, no API key needed)
iro run input.yaml --mode llm --provider ollama --model llama3

# OpenAI
iro run input.yaml --mode llm --provider openai --model gpt-4o

# Gemini
iro run input.yaml --mode llm --provider gemini --model gemini-1.5-pro

# Write to file
iro run input.yaml --mode llm --provider ollama --model llama3 --output report.md

# Split-file mode + LLM
iro run --tests test_suite.yaml --sprint sprint.yaml --mode llm --provider ollama --model llama3
```

### Step 2 — Compare mode

Run both pipelines and receive a side-by-side comparison in one command:

```bash
iro run input.yaml --mode compare --provider ollama --model llama3
```

Output structure:

```
## Comparison Summary

LLM Recommendation Mode: llm
Repairs Applied: 0

## Deterministic Output

<deterministic report>

## LLM Output

<llm report>
```

### Step 3 — Persistent configuration with a config file

Store provider settings in `llm.yaml` (do not include `api_key` — use the env var):

```yaml
provider: ollama
model: llama3
base_url: http://localhost:11434
temperature: 0.3
max_tokens: 4096
```

```bash
iro run input.yaml --mode llm --config llm.yaml
```

Config resolution order (last wins): defaults → config file → env vars → `--provider`/`--model`/`--temperature`/`--max-tokens` CLI flags.

### Step 4 — Interpret the Recommendation Mode label

The `Recommendation Mode:` label in the report header shows which path was taken:

| Value | Meaning |
|---|---|
| `Recommendation Mode: llm` | LLM output passed validation; used as-is |
| `Recommendation Mode: llm-repaired` | LLM output had structural issues; repaired automatically |
| `Recommendation Mode: deterministic-fallback` | LLM failed completely; deterministic report used |

All three paths exit 0 — the report is always structurally valid. Use this label to audit which path ran.

### Exit codes in LLM mode

| Exit Code | Meaning |
|---|---|
| 0 | Report generated (llm, llm-repaired, deterministic-fallback, or deterministic) |
| 2 | Input error — bad config file, invalid flags, missing API key |

All LLM paths — including provider exceptions (network error, authentication failure, timeout) — produce a valid report and exit 0 via the deterministic fallback. Exit 2 covers CLI-level input errors only.

---

## CLI Reference

### `iro run`

```
Usage: iro run [OPTIONS] [INPUT_FILE]
       iro run --tests TESTS_FILE --sprint SPRINT_FILE [OPTIONS]
```

Run the optimisation pipeline on INPUT_FILE and print the report.

Alternatively, supply a test suite and sprint context as separate files using `--tests` and `--sprint`.

Supply `--history-dir` or `--history-file` to overlay CI-derived flakiness metrics onto the test suite before scoring.

Supply `--area-map` with `--diff-file` or `--ref` to auto-derive `changed_areas` from a git diff.

**Single-file mode:**

| Option | Description |
|---|---|
| `--output, -o <path>` | Write report to file instead of stdout |
| `--mode deterministic\|llm\|compare` | Recommendation mode (default: `deterministic`) |
| `--provider openai\|ollama\|gemini` | LLM provider (required when `--mode llm` or `compare`) |
| `--model <name>` | LLM model identifier (e.g. `llama3`, `gpt-4o`, `gemini-1.5-pro`) |
| `--base-url <url>` | LLM provider base URL override (useful for local/proxy deployments) |
| `--temperature <float>` | LLM sampling temperature (default: 0.3) |
| `--max-tokens <int>` | LLM max response tokens (default: 4096) |
| `--config <path>` | Path to LLM config YAML (provider settings; must not contain `api_key`) |
| `--summary-only` | Output only the `## Optimisation Summary` section |
| `--history-dir <path>` | Directory of JUnit XML files (one file per CI run); derives flakiness metrics automatically |
| `--history-file <path>` | Pre-computed history file (`.csv` or `.json`) with flakiness metrics |
| `--area-map <path>` | area-map.yaml config; requires `--diff-file` or `--ref` |
| `--diff-file <path>` | File containing `git diff --name-only` output |
| `--ref <git-ref>` | Git ref to diff against (runs `git diff --name-only <ref>`) |

**Split-file mode (`--tests` + `--sprint`):**

| Option | Description |
|---|---|
| `--tests <path>` | Path to YAML file containing the `test_suite` block |
| `--sprint <path>` | Path to YAML file containing `sprint_context` and `constraints` |
| `--output, -o <path>` | Write report to file instead of stdout |
| `--mode deterministic\|llm\|compare` | Recommendation mode (default: `deterministic`) |
| `--provider openai\|ollama\|gemini` | LLM provider |
| `--model <name>` | LLM model identifier |
| `--base-url <url>` | LLM provider base URL override |
| `--temperature <float>` | LLM sampling temperature |
| `--max-tokens <int>` | LLM max response tokens |
| `--config <path>` | Path to LLM config YAML |
| `--summary-only` | Output only the `## Optimisation Summary` section |
| `--history-dir <path>` | Directory of JUnit XML files |
| `--history-file <path>` | Pre-computed history file (`.csv` or `.json`) |
| `--area-map <path>` | area-map.yaml config; requires `--diff-file` or `--ref` |
| `--diff-file <path>` | File containing `git diff --name-only` output |
| `--ref <git-ref>` | Git ref to diff against |

**History flag rules:**
- `--history-dir` and `--history-file` are mutually exclusive.
- When a test ID in history matches a test in the YAML, `flakiness_rate` is replaced by the history value; `failure_count_last_30d` and `total_runs` are added.
- A `[history-override]` warning is printed to **stderr** for each test where the YAML and history values differ.
- Tests absent from history are left unchanged.

**Area-map flag rules:**
- `--area-map` requires exactly one of `--diff-file` or `--ref`.
- `--diff-file` and `--ref` are mutually exclusive.
- If `--ref` is given, `git diff --name-only <ref>` is run from the current working directory.

**LLM mode flag rules:**
- `--mode llm` and `--mode compare` require `--provider` or a config file that specifies a provider.
- `--provider openai` and `--provider gemini` require the `IRO_LLM_API_KEY` environment variable.
- `--provider ollama` does not require an API key.
- `--config` must not contain an `api_key` field — use `IRO_LLM_API_KEY` for all providers.
- Config resolution order: defaults → config file → env vars → CLI flags (last wins).
- Structural repair and deterministic fallback both exit 0; they are transparent recovery paths.

| Exit Code | Meaning |
|---|---|
| 0 | Success — report generated |
| 1 | Validation error — output contract violated (internal error) |
| 2 | Input error — file not found, parse failure, validation failure, or bad flag combination |

### `iro diff-areas`

```
Usage: iro diff-areas --area-map AREA_MAP (--diff-file FILE | --ref GIT_REF)
```

Derive `changed_areas` from a git diff and print a YAML fragment.

| Option | Required | Description |
|---|---|---|
| `--area-map <path>` | Yes | area-map.yaml config mapping glob patterns to coverage area names |
| `--diff-file <path>` | One of | File containing `git diff --name-only` output |
| `--ref <git-ref>` | One of | Git ref; runs `git diff --name-only <ref>` |

Output example:

```yaml
changed_areas:
- Checkout
- Payments
```

| Exit Code | Meaning |
|---|---|
| 0 | Success — YAML fragment printed |
| 2 | Input error — bad area-map, missing diff file, git failure, or bad flag combination |

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
- **Single-diff area override** — `--area-map` replaces `changed_areas` on all stories; per-story diff mapping is not supported
- **No Jira/TestRail connector** — sprint context must be written by hand or imported via Excel
- **Story `type` not scored** — carried in input for future use only
