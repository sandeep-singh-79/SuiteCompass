# Session Plan

> **Purpose:** Track the active planning and execution steps for the `intelligent-regression-optimizer` repository.
> **Scope:** Session-specific or cycle-specific. Refresh as milestones move.
> **Last Updated:** 2026-04-18

---

## Session Details

| Field | Value |
|---|---|
| Capability | intelligent-regression-optimizer |
| Objective | Phase 1 MVP COMPLETE |
| Current Phase | Phase 1 DONE — awaiting Phase 2 scoping |
| Current Focus | Decide: merge feature branch or begin Phase 2 (LLM integration) |
| Last Updated | 2026-04-18 |

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

### Doc Tracks

| Track | Goal | Status | Notes |
|---|---|---|---|
| D1 - README | Repo overview, install, quick-start, CLI reference | Not Started | Public-facing entry point |
| D2 - USAGE-GUIDE | End-to-end run instructions, exit codes, flags, modes | Not Started | Mirror QEStrategyForge pattern |
| D3 - V1-INPUT-TEMPLATE | Full input schema with field-level annotations | Not Started | Canonical input reference |
| D4 - V1-OUTPUT-TEMPLATE | Annotated sample output report | Not Started | All 6 sections + 7 labels explained |
| D5 - DECISION-RULES | Scoring formula, tier logic, override rules, retire logic | Not Started | Machine-checkable rules, not prose |
| D6 - SCENARIO-LIBRARY | 6+ named scenarios with context, expected output shape, and tradeoffs | Not Started | Mirror QEStrategyForge SITUATIONS-CATALOGUE |
| D7 - VALIDATION-HARNESS | How benchmarks work, how to add a new one, pass/fail criteria | Not Started | Developer guide |
| D8 - LEARNING-GUIDE | How to think about regression prioritisation; suite health concepts | Not Started | Tutorial layer — teaches the domain, not just the tool |
| D9 - PHASED-IMPLEMENTATION | Retrospective: what was built in each phase and why | Not Started | Architectural decision log |

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
| A1 - Excel Template | Sample .xlsx with correct column headers + example rows | Not Started | Ships with repo under templates/ |
| A2 - Excel Loader | `excel_loader.py` — reads .xlsx, maps columns to test_suite schema, outputs YAML | Not Started | openpyxl dependency |
| A3 - CLI `import-tests` | `iro import-tests tests.xlsx --output test_suite.yaml` subcommand | Not Started | Generates test_suite section only |
| A4 - Merge Utility | `iro run --tests test_suite.yaml --sprint sprint.yaml` or auto-merge | Not Started | Optional convenience; manual merge is fallback |
| A5 - Validation | Validate Excel columns, report missing/invalid data with row numbers | Not Started | Same rigour as YAML input validation |
| A6 - Tests + Benchmarks | >=15 tests; sample .xlsx in benchmarks/ | Not Started | TDD: red, green, refactor |

### Column Mapping (default)

| Excel Column | YAML Field | Required | Notes |
|---|---|---|---|
| ID | id | Yes | |
| Name | name | Yes | |
| Layer | layer | Yes | e2e, integration, unit, security, performance |
| Coverage Areas | coverage_areas | Yes | Comma-separated |
| Execution Time (secs) | execution_time_secs | Yes | Numeric |
| Flakiness Rate | flakiness_rate | Yes | 0.0 – 1.0 |
| Failure Count (30d) | failure_count_last_30d | No | Default 0 |
| Automated | automated | No | Default true |
| Tags | tags | No | Comma-separated |

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
