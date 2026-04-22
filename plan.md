# Session Plan

> **Purpose:** Track the active planning and execution steps for the `intelligent-regression-optimizer` repository.
> **Scope:** Session-specific or cycle-specific. Refresh as milestones move.
> **Last Updated:** 2026-04-25

---

## Session Details

| Field | Value |
|---|---|
| Capability | intelligent-regression-optimizer |
| Objective | MVP SEALED |
| Current Phase | All phases (V1-A + V1-B + V1-C) complete |
| Current Focus | Pre-seal review remediation complete. Provider-exception fallback, summary-only mode, prompt context enrichment, benchmark narrative assertions, vacuous-test cleanup, and doc reconciliation are all green. Full regression passed: 562 tests, 96.47% coverage. Next: merge/tag or run final acceptance review before release. |
| Last Updated | 2026-04-25 |

---

## Active Remediation Plan

> **Status:** Complete.
> **Scope:** Review findings were implemented, validated, and folded back into docs and governance.
> **Execution rule:** Completed using red -> green -> refactor, targeted validation per track, then full regression.

### Execution Order

| Order | Track | Priority | Effort | Depends On | Status |
|---|---|---|---|---|---|
| R1 | diff-areas contract alignment | Critical | Small | None | **Complete** |
| R2 | history override visibility | Critical | Small-Medium | None | **Complete** |
| R3 | JUnit timestamp rule reconciliation | Critical | Medium | None | **Complete** |
| R4 | V1-A history benchmark artifact | Major | Medium | R2, R3 | **Complete** |
| R5 | README + supporting doc catch-up | Major | Small-Medium | R1, R3, R4 | **Complete** |

**Outcome:** All remediation tracks are complete and the full regression gate passed at 562 tests / 96.47% coverage. This section remains as historical record only.

### Track R1 - diff-areas Contract Alignment

**Goal:** Make implementation, tests, help text, and docs agree on the `iro diff-areas` contract.

**Sub-tasks:**
1. Decide the product contract:
   - Option A: `iro diff-areas --area-map <path>` defaults to `HEAD~1`
   - Option B: explicit `--diff-file` or `--ref` remains mandatory
2. Update `cli.py` to match the chosen contract exactly.
3. Update `tests/test_diff_areas_cli.py` so tests validate the final contract rather than the current mismatch.
4. Update user-facing wording in CLI help and `docs/USAGE-GUIDE.md`.
5. Run targeted CLI tests for `diff-areas` and `iro run --area-map`.

**Validation:**
- Help text, implementation, and tests describe the same behavior.
- At least one targeted test covers the final no-arg/default-ref or explicit-ref behavior, depending on the decision.

### Track R2 - history Override Visibility

**Goal:** Ensure history-derived overrides are visible to the operator without changing the deterministic markdown output contract.

**Sub-tasks:**
1. Trace the override path from `merge_history()` through CLI rendering.
2. Choose the surfacing mechanism:
   - stderr warnings from CLI
   - logging
   - both, if still simple
3. Stop discarding override warnings returned by `merge_history()`.
4. Preserve markdown report determinism and avoid contaminating report output.
5. Add tests proving override visibility when YAML flakiness differs from history values.
6. Re-run targeted end-to-end history overlay tests.

**Validation:**
- A history override is operator-visible.
- Markdown output still passes the existing output validator unchanged.
- Tests assert both override behavior and warning visibility.

### Track R3 - JUnit Timestamp Rule Reconciliation

**Goal:** Make the code, tests, and plan agree on how `failure_count_last_30d` is derived.

**Decision:** Suite-level timestamps only. Testcase-level timestamp support out-of-scope for V1-A.

**Resolution:**
- `junit_xml_parser.py` reads the `timestamp` attribute on `<testsuite>` elements only.
- Runs with no timestamp are included conservatively (counted within last-30d).
- 23 targeted parser tests cover suite-level timestamps, missing timestamps, and unparseable timestamps.
- Tests 15–17 in `test_junit_xml_parser.py::TestParseJunitDirectory` directly cover timestamp-based `failure_count_last_30d`.
- Plan and docs now state suite-level timestamps explicitly. Testcase-level is deferred to a future increment.

**Status:** COMPLETE (narrowed scope, docs updated)

### Track R4 - V1-A History Benchmark Artifact

**Goal:** Add the planned regression anchor proving history-backed behavior end-to-end.

**Dependencies:** R2 and R3 must be complete first so the benchmark targets final behavior.

**Sub-tasks:**
1. Create `benchmarks/with-history/`.
2. Add realistic sample JUnit XML files covering at least:
   - one flaky test
   - one stable test
   - one recommendation shift driven by history
3. Add input YAML designed to differ meaningfully with and without history applied.
4. Add assertions YAML proving the intended history-driven output.
5. Add or update tests to exercise the benchmark end-to-end.
6. Confirm all existing benchmarks still pass unchanged.

**Validation:**
- `benchmarks/with-history/` exists with XML inputs, input YAML, and assertions.
- There is objective proof that `--history-dir` changes output as intended.

### Track R5 - README + Supporting Doc Catch-Up

**Goal:** Close the remaining planned documentation gaps once behavior is stable.

**Dependencies:**
- R1 finalizes the `diff-areas` contract.
- R3 finalizes timestamp semantics.
- R4 provides the committed benchmark artifact.

**Sub-tasks:**
1. Update `README.md` CLI reference with shipped V1-A / V1-B flags and `iro diff-areas`.
2. Update `docs/SCORING-FORMULA.md` with the history-precedence note promised in A3.
3. Update `docs/BENCHMARK-AUTHORING.md` with conventions for history-backed benchmarks.
4. Re-check `docs/USAGE-GUIDE.md` for consistency with the final `diff-areas` contract.
5. Verify all examples and command snippets against the final implementation.

**Validation:**
- README is no longer stale relative to the shipped CLI.
- The plan-promised V1-A / V1-B documentation updates exist and are accurate.

### Global Execution Rules For R1-R5

1. Follow TDD strictly: failing test first, then implementation, then refactor.
2. Run targeted tests after each track before moving to the next track.
3. Keep fixes minimal and root-cause oriented; do not broaden scope into low/trivial cleanup.
4. Preserve deterministic report structure unless a track explicitly requires otherwise.
5. After R5, run full regression and perform a fresh acceptance review against the original findings.

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

---

## v1.0 Implementation Plan

### Objective

Bring SuiteCompass from v0.3.x (deterministic core) to v1.0 by adding three capability layers:
- V1-A: JUnit XML + test history ingestion
- V1-B: Git diff → coverage area mapper
- V1-C: LLM narrative layer

### Phase Dependencies

```
V1-A (JUnit XML + History)    V1-B (Git Diff Mapper)   ← independent, parallel-safe
        ↘                          ↙
          V1-C (LLM Narrative)                          ← depends on both
```

---

### Engineering Principles (mandatory, enforced per task)

#### Code Quality
- **SOLID** — apply where it helps clarity and testability; don't force abstraction for its own sake
- **DRY** — extract shared logic only when duplication is real (≥2 occurrences), not speculative
- **YAGNI** — implement only what the current slice needs; no speculative extension points
- **KISS** — simple implementations first; design patterns only when complexity genuinely demands them
- **Reuse-first** — extend existing modules before creating new ones; copy-adapt from QEStrategyForge where proven

#### TDD Discipline (red → green → refactor)
- Write failing test first; make it pass; refactor
- Do not mark code complete until tested with reported pass/fail and coverage
- Coverage ≥ 90% per module, measured after each sub-phase
- Every sub-phase ends with: `pytest --tb=short -q` pass + coverage check

#### Review Cycle (mandatory per sub-phase)
- After each sub-phase is green: self-review the code for issues
- Fix all issues found before proceeding to next sub-phase
- Iterate review → fix until clean
- Check: no dead code, no unused imports, no over-abstraction, no missing edge cases

#### Documentation Discipline (mandatory per task)
- Update docs when a task adds user-visible capability or changes behaviour
- USAGE-GUIDE: update CLI reference, add new workflow sections
- LEARNING-GUIDE: add domain explanation when new concepts are introduced
- SCORING-FORMULA: update if score inputs change
- BENCHMARK-AUTHORING: update if benchmark conventions change
- V1-INPUT-TEMPLATE: update validation rules when input schema changes
- README: update Development Status table and CLI table after each phase
- Do not defer documentation — it ships with the code

#### Inherited Practices (from QEStrategyForge, validated)
- `from __future__ import annotations` at top of every module
- Type hints on all function signatures
- `@dataclass(slots=True)` for data structures
- Path security: `Path.resolve()` + `is_relative_to(root)` for any user-supplied paths
- Protocol-based client boundaries (typing.Protocol + @runtime_checkable) for LLM clients
- Repo-local temp paths (`tmp/` gitignored), never OS temp dirs
- API keys only from env vars, never config files
- Error codes: 0=success, 1=IO error, 2=validation error, 3=generation error
- Binary benchmark assertions only — pass/fail, no weighted scoring
- Composition root in CLI; dependencies passed as arguments
- Minimal external dependencies (stdlib + PyYAML + click + openpyxl)

---

### Phase V1-A: JUnit XML + Test History Ingestion

**Goal:** Eliminate manual flakiness_rate / failure_count_last_30d entry.
**Branch:** `v1a-test-history`
**Decisions:** Both adapters — raw JUnit XML parser AND pre-computed summary (CSV/JSON).

#### Sub-phase A1: TestHistoryRecord Model + History Loader

**TDD targets:**
1. Add `TestHistoryRecord` dataclass to `models.py`: test_id, flakiness_rate, failure_count_last_30d, total_runs, last_run_date (optional)
2. Implement `history_loader.py`:
   - `load_history_csv(path: str) -> dict[str, TestHistoryRecord]`
   - `load_history_json(path: str) -> dict[str, TestHistoryRecord]`
   - Validate schema: required columns, value ranges (0.0–1.0 for flakiness, non-negative int for failures)
   - Raise `InputValidationError` on bad data
3. Tests (~12): valid CSV, valid JSON, missing columns, out-of-range values, empty file, duplicate test_ids

**Review checkpoint:** code review after green. Fix issues. Iterate.

**Docs:** Update V1-INPUT-TEMPLATE — document pre-computed history format (CSV/JSON schema).

#### Sub-phase A2: JUnit XML Parser

**TDD targets:**
1. Implement `junit_xml_parser.py`:
   - `parse_junit_directory(dir_path: str) -> dict[str, TestHistoryRecord]`
   - Support standard JUnit XML schema (surefire, pytest-junit)
   - Parse N XML files: extract per-test pass/fail per run
   - Compute flakiness heuristic: "failed in run N, passed in run N±1" = flaky occurrence
   - `flakiness_rate = flaky_runs / total_runs`
   - `failure_count_last_30d` from `<testcase>` timestamps (if available) or total failures across all files
   - Use `xml.etree.ElementTree` (stdlib) — no lxml dependency
2. Tests (~15): sample XML fixtures in `tests/fixtures/junit-xml/`, empty dir, malformed XML, no timestamp, single file, mixed pass/fail across runs, tests appearing in some files but not others

**Review checkpoint:** code review after green. Fix issues. Iterate.

**Docs:**
- LEARNING-GUIDE: add subsection to "Reading Suite Health Signals" explaining how flakiness is computed from CI history (heuristic, limitations, manual override).
- USAGE-GUIDE: document `--history-dir` workflow.

#### Sub-phase A3: History Merge + Pipeline Wiring

**TDD targets:**
1. Add `merge_history()` to `input_loader.py`:
   - `merge_history(normalized: dict, history: dict[str, TestHistoryRecord]) -> dict`
   - For each test in test_suite: if history record exists, override flakiness_rate and failure_count_last_30d
   - History wins over manual values (emit warning via logging)
   - Tests with no history record keep manual values (or defaults)
2. Wire into `end_to_end_flow.py`:
   - Accept optional `history` parameter in `run_pipeline()` / `run_pipeline_from_merged()`
   - Call `merge_history()` before `classify_context()` step
3. Tests (~8): merge override logic, missing tests, manual vs history precedence, empty history dict, history with unknown test_ids (ignored)

**Review checkpoint:** code review after green. Fix issues. Iterate.

**Docs:** SCORING-FORMULA — add note that flakiness_rate can be history-derived or manual, with history taking precedence.

#### Sub-phase A4: CLI Flags + Benchmark

**TDD targets:**
1. Add CLI flags to `iro run`:
   - `--history-dir <path>` → calls `parse_junit_directory()`
   - `--history-file <path>` → calls `load_history_csv()` or `load_history_json()` (detect by extension)
   - Both optional; existing YAML-only path unchanged
   - Mutual exclusion: cannot use both simultaneously
2. Create benchmark: `benchmarks/with-history/` directory containing sample JUnit XML files + input YAML + assertions
3. Tests (~8): CLI flag wiring, error messages for bad paths, mutual exclusion, end-to-end with history

**Review checkpoint:** code review after green. Fix issues. Iterate.

**Docs:**
- USAGE-GUIDE: add Workflow 4 (CI History Import) — step-by-step for both XML and pre-computed paths.
- README: update CLI table with new flags.
- BENCHMARK-AUTHORING: add note about benchmarks that include history directories.

#### Sub-phase A5: Phase A Hardening

1. Coverage check: all new modules ≥ 90%
2. Run all 3 existing benchmarks — must still pass unchanged (no regression)
3. Run new history benchmark — must pass
4. Review all A1–A4 code holistically: dead code, edge cases, error messages
5. Fix any issues found. Iterate until clean.

**Verification:**
- `python -m pytest --tb=short -q` — all tests pass
- `iro run benchmarks/high-risk-feature-sprint.input.yaml` — identical to v0.3.x output
- `iro run benchmarks/high-risk-feature-sprint.input.yaml --history-dir benchmarks/with-history/` — output reflects history-derived values
- All modules ≥ 90% coverage

---

### Phase V1-B: Git Diff → Coverage Area Mapper ✅ COMPLETE

**Goal:** Derive changed_areas from git diff instead of manual declaration.
**Branch:** `v1b-diff-mapper`
**Decisions:** Lightweight git-diff mapper with config file. CI webhook backlogged.

#### Sub-phase B1: Area Mapping Config + Mapper ✅ COMPLETE
Commit: `095bddc` — 35 tests, 100% coverage.

#### Sub-phase B2: CLI Subcommand + iro run Integration ✅ COMPLETE
Commit: `9fedd32` — 394 tests (19 new), 97.18% coverage.
- `iro diff-areas` subcommand added
- `iro run --area-map / --diff-file / --ref` flags wired
- `end_to_end_flow.run_pipeline()` + `run_pipeline_from_merged()` accept `changed_areas`

#### Sub-phase B3: Phase B Hardening ✅ COMPLETE
Commit: `58e2542`
- `templates/area-map.yaml` sample file added
- `docs/USAGE-GUIDE.md` — Workflow 4 (History) + Workflow 5 (Git Diff) added; CLI reference updated; Limitations updated
- `docs/V1-INPUT-TEMPLATE.md` — area-map.yaml schema documented

---

### Phase V1-C: LLM Narrative Layer

**Goal:** Add LLM prose explanations to deterministic report. Default enhances report; `--summary-only` for executive summary.
**Branch:** `v1c-llm-narrative`
**Decisions:** Copy-adapt from QEStrategyForge. Deterministic fallback non-negotiable.

#### Sub-phase C1: Client Infrastructure (copy-adapt)

**TDD targets:**
1. Copy-adapt from QEStrategyForge (rename env prefix to `IRO_LLM_*`):
   - `llm_client.py` — LLMClient Protocol, GenerationRequest, GenerationResponse
   - `ollama_client.py` — verbatim
   - `openai_client.py` — verbatim
   - `gemini_client.py` — verbatim
   - `client_factory.py` — verbatim
   - `config_loader.py` — adapt env prefix, default model
2. Tests (~15): copy-adapt from QEStrategyForge test patterns. FakeLLMClient for structural tests. Config 4-layer resolution. Factory dispatch.

**Review checkpoint:** verify copied code compiles, tests pass, no stale QEStrategyForge references.

**Docs:** None needed yet (internal infrastructure).

#### Sub-phase C2: Prompt Builder + Templates

**TDD targets:**
1. Implement `prompt_builder.py`:
   - `build_prompt(normalized, classifications, tier_result, mode) -> str`
   - `mode`: "enhanced" (prose per section) or "summary_only" (executive summary)
   - Template-based: load from `prompts/v1/enhance.txt` and `prompts/v1/summary.txt`
   - Prompt includes: sprint context summary, classification results, full tier lists with scores, override reasons, retire candidate rationale, budget overflow status, history provenance (manual vs CI-derived)
2. Create prompt templates in `prompts/v1/`:
   - `enhance.txt` — instructions for injecting prose explanations after each tier section
   - `summary.txt` — instructions for standalone executive summary
   - Both include output contract (required headings + labels) and no-invention guard
3. Tests (~10): template rendering with all fields, missing optional fields, mode selection, prompt includes all required context

**Review checkpoint:** code review after green. Fix issues. Iterate.

**Docs:** None yet (prompts are internal).

#### Sub-phase C3: LLM Flow + Repair + Fallback

**TDD targets:**
1. Implement `llm_flow.py`:
   - `run_llm_pipeline(input_path, llm_client, config, mode) -> FlowResult`
   - Pipeline: load → classify → score → render (deterministic) → build prompt → call LLM → validate → repair → fallback
   - Repair: inject missing headings/labels from deterministic output (structural only, no content synthesis)
   - Fallback: return deterministic output on any LLM failure (exit code 0, not 3)
   - For `summary_only`: LLM produces executive summary, prepended before deterministic report
2. Copy-adapt `comparison.py` from QEStrategyForge — deterministic vs LLM side-by-side
3. Tests (~20): FakeLLMClient happy path, partial output → repair, total failure → deterministic fallback, summary-only mode, comparison output format

**Review checkpoint:** code review. Verify fallback chain fires correctly. Fix issues. Iterate.

**Docs:** SCORING-FORMULA — add note that LLM narrative does not alter scores or tier assignments (it explains them).

#### Sub-phase C4: CLI Flags + Live Testing

**TDD targets:**
1. Add CLI flags to `iro run`:
   - `--mode deterministic|llm` (default: deterministic)
   - `--provider ollama|openai|gemini` (required when mode=llm)
   - `--model <name>`
   - `--summary-only` (available with any mode)
   - `--compare <output.md>` (side-by-side comparison)
2. Wire composition root: CLI resolves config → creates client → calls `run_llm_pipeline()`
3. Tests (~8): CLI flag wiring, mode validation, missing provider error, deterministic mode unchanged
4. Live tests (marked `@pytest.mark.live`, excluded by default): Ollama smoke test with real model

**Review checkpoint:** end-to-end with Ollama. Fix issues. Iterate.

**Docs:**
- USAGE-GUIDE: add Workflow 6 (LLM-Enhanced Report) — step-by-step, provider setup, summary-only mode, comparison mode.
- LEARNING-GUIDE: add section "How to Read an LLM-Enhanced Report" — what the narrative adds, why deterministic scores are still authoritative, how fallback works.
- README: update CLI table with `--mode`, `--provider`, `--model`, `--summary-only`, `--compare` flags.

#### Sub-phase C5: Phase C Hardening

1. Coverage check: all new modules ≥ 90%
2. All existing benchmarks pass unchanged (deterministic path untouched)
3. LLM benchmark: `benchmarks/llm-enhanced-high-risk.assertions.yaml` with narrative presence assertions
4. Kill LLM mid-request → verify deterministic fallback fires, valid output produced
5. Review all C1–C4 code holistically. Fix issues. Iterate.

**Verification:**
- All tests pass
- `iro run input.yaml --mode deterministic` — identical to v0.3.x
- `iro run input.yaml --mode llm --provider ollama` — enhanced report with prose
- `iro run input.yaml --mode llm --summary-only` — summary section of LLM-enhanced report
- All modules ≥ 90% coverage

---

### Final Phase: v1.0 Seal

1. Update pyproject.toml version to 1.0.0
2. Update README Development Status (test count, coverage, phase summary)
3. Update PHASED-IMPLEMENTATION with V1-A, V1-B, V1-C retrospective
4. Full test suite pass + all benchmarks green
5. Tag `v1.0.0` on master
6. Update program-level memory

---

### Scope Boundaries

**Included:**
- JUnit XML parser (surefire + pytest-junit), pre-computed CSV/JSON history
- Git diff → coverage area glob mapper with config file
- 3-provider LLM (ollama, openai, gemini) with narrative injection + executive summary
- Deterministic fallback on all LLM failures
- All existing v0.3.x behaviour preserved unchanged
- Documentation updated per task

**Excluded (backlogged):**
- CI webhook listener (future, after V1-B proves mapping)
- Multi-hop dependency traversal
- Fuzzy coverage_areas matching
- PyPI publish
- Configurable scoring weights
- Karpathy optimization loop for SuiteCompass prompts
- AST-level / method-level change detection

### Estimated New Tests

| Phase | New Tests | Cumulative |
|---|---|---|
| V1-A (5 sub-phases) | ~43 | ~291 |
| V1-B (3 sub-phases) | ~22 | ~313 |
| V1-C (5 sub-phases) | ~53 | ~366 |
| Total | ~118 | ~366 |
