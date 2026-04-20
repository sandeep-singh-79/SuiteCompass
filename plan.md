# Session Plan

> **Purpose:** Track the active planning and execution steps for the `intelligent-regression-optimizer` repository.
> **Scope:** Session-specific or cycle-specific. Refresh as milestones move.
> **Last Updated:** 2026-04-18

---

## Session Details

| Field | Value |
|---|---|
| Capability | intelligent-regression-optimizer |
| Objective | MVP SEALED |
| Current Phase | All phases (1 + 2 + 3) complete |
| Current Focus | docs-fix-review-gaps branch merged; ready for next capability |
| Last Updated | 2026-04-21 |

---

## Plan Tracks (TDD: red -> green -> refactor)

| Track | Goal | Status | Notes |
|---|---|---|---|
| T1 - Repo Setup | Git init, memory layer, AGENTS.md, plan.md | Complete | |
| T2 - Product Definition | Problem statement, inputs, outputs, non-goals | Complete | Locked 2026-04-17 |
| T3 - Python Scaffold | pyproject.toml, src layout, models.py | Complete | 11 tests |
| T4 - Output Contract | output_validator.py + test (>=15) | Complete | 21 tests |
| T5 - Input Loader | input_loader.py + test (>=15) | Complete | 22 tests |
| T6 - Context Classifier | context_classifier.py + test (>=12) | Complete | 17 tests |
| T7 - Scoring Engine | scoring_engine.py + test (>=22) | Complete | 34 tests |
| T8 - Renderer | renderer.py + test (>=12) | Complete | 13 tests + 5 integration |
| T9 - Benchmarks | 3x input + assertions YAMLs | Complete | 3 scenarios |
| T10 - E2E Flow | end_to_end_flow.py, benchmark_runner.py | Complete | 11 tests |
| T11 - CLI | cli.py + test (>=8) | Complete | 13 tests |
| T12 - Hardening | all modules >=90%, all benchmarks green | Complete | 99.07% coverage |

---

## MVP Acceptance Criteria (all PASSED)

1. [x] 3 benchmark assertion files pass via benchmark_runner
2. [x] All modules >=90% coverage (total 99.10%)
3. [x] 166 tests passing (target was >=110)
4. [x] output_validator.validate_output() passes for every benchmark output
5. [x] CLI iro run returns exit 0 for valid input, exit 2 for invalid
6. [x] CLI iro benchmark returns exit 0 for passing assertions, exit 1 for failing

---

## Final Commit

Branch: phase-1-deterministic-core
HEAD: (pending commit)
Message: fix: address review — temp-path compliance, input validation, retire display (166 tests, 99.1% coverage)

---

## Next: Phase 2 Options

- Option A: Merge phase-1-deterministic-core to master
- Option B: Begin Phase 2 scoping (LLM narrative integration, real JUnit XML ingestion)
- Option C: Publish the package (pypi, documentation)

---

## Phase 2 — Documentation and Learning Tutorials

Mirrors the documentation and learning layer built for QEStrategyForge.

**Objective:** Provide complete documentation for all implemented functionality (Phase 1 + Phase 3) plus a domain learning tutorial.

**Deliverables:** 9 documentation files (D1–D9) covering usage, schemas, decision rules, scenarios, validation, learning, and retrospective.

**Dependencies:** Phase 1 deterministic core (scoring formula, output contract, CLI) and Phase 3 Excel adapter (import-tests command, template, column mapping).

**Success Metrics:**
- README quick-start works from a fresh clone (`iro run tests/fixtures/valid_input.yaml` exits 0)
- USAGE-GUIDE covers all 3 CLI subcommands, all flags, all exit codes (0/1/2)
- V1-INPUT-TEMPLATE documents every validated field from `input_loader.py`
- V1-OUTPUT-TEMPLATE lists all 6 headings + 7 labels from `output_validator.py`
- DECISION-RULES scoring formula matches `memory.md` verbatim
- SCENARIO-LIBRARY has ≥6 named scenarios with context + expected behaviour
- VALIDATION-HARNESS assertion schema fully documented
- LEARNING-GUIDE has ≥5 sections + ≥3 hands-on exercises
- PHASED-IMPLEMENTATION has Phase 1 + Phase 3 retrospectives
- All doc files cross-linked from README documentation index

**Exit Criteria:** All 9 doc tracks marked Complete; all success metrics pass; governance artifacts (plan.md, memory.md) updated to reflect delivery.

### Doc Tracks

| Track | Goal | Status | Notes |
|---|---|---|---|
| D1 - README | Repo overview, install, quick-start, CLI reference | Complete | Public-facing entry point |
| D2 - USAGE-GUIDE | End-to-end run instructions, exit codes, flags, modes | Complete | Covers all 3 subcommands + Excel import workflow |
| D3 - V1-INPUT-TEMPLATE | Full input schema with field-level annotations | Complete | Canonical input reference incl. passthrough fields |
| D4 - V1-OUTPUT-TEMPLATE | Annotated sample output report | Complete | All 6 sections + 7 labels explained |
| D5 - DECISION-RULES | Scoring formula, tier logic, override rules, retire logic | Complete | Machine-checkable rules with full formula |
| D6 - SCENARIO-LIBRARY | 6+ named scenarios with context, expected output shape, and tradeoffs | Complete | 7 named scenarios + comparison matrix |
| D7 - VALIDATION-HARNESS | How benchmarks work, how to add a new one, pass/fail criteria | Complete | Developer guide with step-by-step |
| D8 - LEARNING-GUIDE | How to think about regression prioritisation; suite health concepts | Complete | 6 sections + 5 hands-on exercises |
| D9 - PHASED-IMPLEMENTATION | Retrospective: what was built in each phase and why | Complete | Architecture decision log + Phase 1/3/2 retros |

### Learning Tutorial Scope (D8 — LEARNING-GUIDE)

The learning guide should teach regression suite thinking, not just tool usage. Cover:

1. Why oversized regression suites hurt delivery
   - CI time inflation
   - flakiness noise masking real failures
   - manual triage overhead
2. How sprint context changes the right test selection
   - risk level and coverage area matching
   - NFR elevation triggers
   - dependency test coverage
3. Reading suite health signals
   - flakiness rate thresholds
   - failure count trends
   - unique coverage as a retire signal
4. How to interpret a SuiteCompass report
   - must-run vs should-run vs defer
   - retire candidates and what to do with them
   - budget overflow and time pressure
5. Common mistakes in regression prioritisation
   - running everything by default
   - ignoring flakiness until it is too late
   - retiring tests without checking unique coverage

### Doc Acceptance Criteria

- README installs and runs end-to-end from a clean clone
- USAGE-GUIDE covers all CLI flags, both subcommands, and all exit codes
- SCENARIO-LIBRARY has >=6 named scenarios, each with context + expected behaviour
- LEARNING-GUIDE has >=5 sections teaching regression thinking
- All doc files are linked from README

---

## Phase 3 — Excel Import Adapter

Enable teams to feed their existing test inventory from spreadsheets instead of hand-writing YAML.

### Adapter Tracks

| Track | Goal | Status | Notes |
|---|---|---|---|
| A1 - Excel Template | Sample .xlsx with correct column headers + example rows | Complete | `templates/test_suite_template.xlsx` — 13 columns, 5 example rows |
| A2 - Excel Loader | `excel_loader.py` — reads .xlsx, maps columns to test_suite schema, outputs YAML | Complete | Strict validation: blank required cells raise; malformed optional cells raise |
| A3 - CLI `import-tests` | `iro import-tests tests.xlsx --output test_suite.yaml` subcommand | Complete | Emits test_suite section only; merge with sprint YAML manually |
| A4 - Merge Utility | `iro run --tests test_suite.yaml --sprint sprint.yaml` or auto-merge | Complete | CLI `run` accepts --tests + --sprint flags; merges and validates before pipeline |
| A5 - Validation | Validate Excel columns, report missing/invalid data with row numbers | Complete | Blank required cells raise; malformed typed optional cells raise |
| A6 - Tests + Benchmarks | >=15 tests; sample .xlsx in benchmarks/ | Complete | 245 tests; `benchmarks/sample-import.xlsx` added |

### Column Mapping (default)

| Excel Column | YAML Field | Required | Notes |
|---|---|---|---|
| ID | id | Yes | |
| Name | name | Yes | |
| Layer | layer | Yes | e2e, integration, unit, security, performance |
| Coverage Areas | coverage_areas | Yes | Comma-separated |
| Execution Time (secs) | execution_time_secs | Yes | Numeric |
| Flakiness Rate | flakiness_rate | Yes | 0.0 – 1.0 |
| Failure Count (30d) | failure_count_last_30d | No | Default 0; malformed values raise |
| Automated | automated | No | Default true; malformed values raise |
| Tags | tags | No | Comma-separated |
| Priority | priority | No | Passthrough — P0/P1/P2/P3; not used in scoring |
| External ID | external_id | No | Passthrough — Jira/TestRail ref; fuzzy aliases: jira, testrailid |
| Owner | owner | No | Passthrough — assignee or team name |
| Module | module | No | Passthrough — component/suite; fuzzy aliases: component, suite, section |

### Adapter Acceptance Criteria

- `iro import-tests sample.xlsx` produces valid test_suite YAML that passes input validation
- Missing required columns fail with clear error message and column name
- Invalid cell values report row number and column
- Round-trip: import .xlsx → merge with sprint YAML → `iro run` → exit 0

---

## Phase 4+ — Future Adapters (not scoped)

| Adapter | Purpose | Trigger |
|---|---|---|
| Jira | Auto-populate sprint_context.stories from sprint board | When adoption justifies API integration |
| JUnit XML | Derive flakiness_rate and failure_count from historical test runs | When teams need automated enrichment |
| TestRail / Zephyr | Direct test management system import | When specific TMS adoption is confirmed |
