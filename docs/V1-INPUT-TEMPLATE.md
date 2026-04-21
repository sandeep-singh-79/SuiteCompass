# V1 Input Template

Canonical input schema reference for SuiteCompass. The tool accepts a single YAML document with three top-level keys.

---

## Top-Level Structure

```yaml
sprint_context:   # Required — sprint stories, risk, and exploratory notes
test_suite:       # Required — list of test entries to score
constraints:      # Required — budget and threshold configuration
```

---

## `sprint_context`

| Field | Type | Required | Description |
|---|---|---|---|
| `sprint_id` | string | Yes | Unique sprint identifier |
| `stories` | list | Yes | Sprint stories to evaluate (see below) |
| `exploratory_sessions` | list | No | Exploratory testing notes (default: `[]`) |

### `stories[]` — each entry

| Field | Type | Required | Default | Valid Values | Description |
|---|---|---|---|---|---|
| `id` | string | Yes | — | — | Unique story identifier |
| `title` | string | Yes | — | — | Human-readable story name |
| `risk` | string | Yes | — | `high`, `medium`, `low` | Story risk level — drives scoring multiplier |
| `type` | string | Yes | — | `feature`, `bugfix`, `refactor`, `tech-debt` | Story type (no scoring impact in Phase 1, carried for future use) |
| `changed_areas` | list[string] | Yes | — | — | Areas modified by this story — matched against test `coverage_areas` |
| `dependency_stories` | list[string] | No | `[]` | IDs from within `stories` | 1-hop dependency references — adds coverage via dep stories' `changed_areas` |

### `exploratory_sessions[]` — each entry

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | string | Yes | Unique session identifier |
| `tester` | string | Yes | Name of the tester |
| `risk_areas` | list[string] | Yes | Areas flagged as risky — amplifies scores for matching tests |
| `notes` | string | No | Free-text observations |

---

## `test_suite[]` — each entry

| Field | Type | Required | Default | Valid Values | Description |
|---|---|---|---|---|---|
| `id` | string | Yes | — | — | Unique test identifier |
| `name` | string | Yes | — | — | Human-readable test name |
| `layer` | string | Yes | — | `e2e`, `integration`, `unit`, `security`, `performance` | Test type layer |
| `coverage_areas` | list[string] | Yes | — | — | Areas this test exercises (comma-separated in Excel) |
| `execution_time_secs` | number | Yes | — | ≥ 0 | Test execution time in seconds |
| `flakiness_rate` | float | Yes | — | 0.0 – 1.0 | Proportion of flaky runs (e.g. 0.05 = 5% flaky) |
| `failure_count_last_30d` | integer | No | `0` | ≥ 0 | Failures in the last 30 days |
| `automated` | boolean | No | `true` | `true`, `false` | Whether the test is automated |
| `tags` | list[string] | No | `[]` | — | Arbitrary tags (e.g. `critical-flow`, `smoke`) |

### Passthrough Fields (optional, not scored)

These fields are accepted via Excel import and carried through to YAML output, but are not used in scoring or tier assignment:

| Field | Type | Description |
|---|---|---|
| `priority` | string | P0/P1/P2/P3 — team-assigned priority |
| `external_id` | string | Jira/TestRail reference (e.g. `JIRA-101`) |
| `owner` | string | Person or team responsible |
| `module` | string | Application module or component |

---

## `constraints`

| Field | Type | Required | Description |
|---|---|---|---|
| `time_budget_mins` | number | Yes | Maximum execution time budget in minutes for scored must-run tests |
| `mandatory_tags` | list[string] | Yes | Tags that force a test to must-run regardless of score |
| `flakiness_retire_threshold` | float | Yes | Tests above this flakiness rate (with no unique coverage) are retire candidates |
| `flakiness_high_tier_threshold` | float | Yes | Threshold for "Flakiness Tier High" count in Suite Health Summary |

---

## Minimal Complete Example

```yaml
sprint_context:
  sprint_id: SPRINT-42
  stories:
    - id: PROJ-1100
      title: Add retry logic to PaymentService
      risk: high
      type: feature
      changed_areas:
        - PaymentService
        - RetryHandler
      dependency_stories:
        - PROJ-1099
    - id: PROJ-1099
      title: Refactor OrderFacade
      risk: medium
      type: refactor
      changed_areas:
        - OrderFacade
        - PaymentService
      dependency_stories: []
  exploratory_sessions:
    - session_id: EX-07
      tester: alice
      risk_areas:
        - RetryHandler
        - PaymentService
      notes: "Observed intermittent timeouts under load"

test_suite:
  - id: TEST-001
    name: payment flow e2e
    layer: e2e
    coverage_areas:
      - PaymentService
      - OrderFacade
    execution_time_secs: 120
    flakiness_rate: 0.05
    failure_count_last_30d: 1
    automated: true
    tags: []
  - id: TEST-002
    name: retry handler integration
    layer: integration
    coverage_areas:
      - RetryHandler
    execution_time_secs: 45
    flakiness_rate: 0.02
    failure_count_last_30d: 0
    automated: true
    tags:
      - critical-flow
  - id: TEST-003
    name: payment service security
    layer: security
    coverage_areas:
      - PaymentService
    execution_time_secs: 90
    flakiness_rate: 0.01
    failure_count_last_30d: 0
    automated: true
    tags: []

constraints:
  time_budget_mins: 20
  mandatory_tags:
    - critical-flow
  flakiness_retire_threshold: 0.30
  flakiness_high_tier_threshold: 0.20
```

---

## Excel Import Alternative

Instead of writing YAML by hand, teams can use the Excel template:

```bash
iro import-tests templates/test_suite_template.xlsx --output test_suite.yaml
```

This produces only the `test_suite:` block. Merge it with your own `sprint_context` and `constraints` YAML before running `iro run`.

See the [USAGE-GUIDE](USAGE-GUIDE.md) for the full Excel import workflow.

---

## Validation Rules

The input loader (`input_loader.py`) enforces these binary checks:

- All three top-level keys (`sprint_context`, `test_suite`, `constraints`) must be present
- `stories` must be a list (may be empty if no stories are defined for the sprint)
- Each story must have `id`, `risk`, `changed_areas` (list), `dependency_stories` (list)
- `risk` must be one of: `high`, `medium`, `low`
- `name` is required on every test
- `layer` must be one of: `e2e`, `integration`, `unit`, `security`, `performance`
- `coverage_areas` must be a non-empty list (in YAML; blank coverage in Excel raises)
- `execution_time_secs` must be a non-negative number
- `flakiness_rate` must be between 0.0 and 1.0
- `dependency_stories` IDs must reference stories defined in the same `sprint_context`
- `test_suite` must be a list (may be empty; an empty suite produces no recommendations)
- `mandatory_tags` must be a list

---

## Pre-Computed Test History (V1-A)

Instead of entering `flakiness_rate` and `failure_count_last_30d` manually in your YAML, you can supply a pre-computed history file. When provided via `--history-file`, the loader overwrites the manual values for any test whose `id` appears in the history file. Tests not in the history file keep their manual values.

### CSV Format

One row per test. Column order does not matter.

| Column | Type | Required | Description |
|---|---|---|---|
| `test_id` | string | Yes | Must match the `id` field in `test_suite` |
| `flakiness_rate` | float 0.0–1.0 | Yes | Fraction of runs where the test was flaky |
| `failure_count_last_30d` | integer ≥ 0 | Yes | Total failures in the last 30 days |
| `total_runs` | integer ≥ 0 | Yes | Total runs in the history window |
| `last_run_date` | string (any date format) | No | Date of most recent run; informational only |

Example:

```csv
test_id,flakiness_rate,failure_count_last_30d,total_runs,last_run_date
T-001,0.05,2,40,2026-04-18
T-002,0.0,0,40,2026-04-18
T-003,0.30,12,40,2026-04-17
```

### JSON Format

A JSON array of objects. Each object must have the same required fields as the CSV columns above.

```json
[
  {"test_id": "T-001", "flakiness_rate": 0.05, "failure_count_last_30d": 2, "total_runs": 40, "last_run_date": "2026-04-18"},
  {"test_id": "T-002", "flakiness_rate": 0.0,  "failure_count_last_30d": 0, "total_runs": 40},
  {"test_id": "T-003", "flakiness_rate": 0.30, "failure_count_last_30d": 12, "total_runs": 40}
]
```

### History Validation Rules

- `test_id` is required in every record
- `flakiness_rate` must be a number between 0.0 and 1.0 (inclusive)
- `failure_count_last_30d` must be a non-negative integer
- `total_runs` must be a non-negative integer
- Duplicate `test_id` values in the same file raise a validation error
- File not found raises a validation error
- History values take precedence over manual YAML values (a warning is logged)
- Tests with no history record keep their manual YAML values unchanged
