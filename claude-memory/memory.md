# Memory

Current state, decisions, and active priorities for the `intelligent-regression-optimizer` capability.

> **Update Policy:** Update this file when the current capability direction, decisions, next actions, or blockers change.
> **Scope:** Capability-specific and durable across sessions for this repository.

---

## Capability Context
- Repository purpose: build an AI-native regression optimizer that analyses test suite history to identify redundant, flaky, and high-risk tests, then recommends prioritisation and pruning decisions to improve release confidence without increasing cycle time.
- Current stage: V1-A and V1-B remain complete and stable. V1-C implementation is feature-rich. Pre-seal review remediation was previously completed, and a follow-on increment added flaky-critical elevation for unique, impacted, medium/high-risk coverage. Full regression now passes at 604 tests, 0 failures.
- Active branch: `feature/flaky-critical-elevation`.
- Next: strategic review of the 5 feature commits, then decide whether to retain the current 5-commit shape or squash further before PR.

## v1.0 Engineering Principles (MANDATORY — enforce per sub-phase, survive compaction)

### Code Quality Rules
- **SOLID** — apply where it aids clarity and testability; never force abstraction speculatively
- **DRY** — extract shared logic only when duplication is real (≥2 actual occurrences)
- **YAGNI** — implement only what the current sub-phase needs; no extension points for hypothetical future use
- **KISS** — simple implementation first; introduce patterns only when complexity genuinely demands them
- **Simple code first, patterns via refactoring** — write the simplest working implementation first. Design patterns are a refactoring tool, not a starting point. Introduce them only when the code's complexity warrants the abstraction, not preemptively.
- **Reuse-first** — extend existing modules before creating new ones; copy-adapt from QEStrategyForge over rebuilding from scratch

### TDD Discipline (NON-NEGOTIABLE)
- Cycle: **Red → Green → Refactor**. Never in any other order.
  - **Red:** Write the failing test first. No production code before a failing test exists.
  - **Green:** Write the *simplest* code that makes the test pass. No premature abstraction.
  - **Refactor:** Clean up. Remove duplication. Introduce design patterns *only here, only when the existing complexity warrants them*. Patterns are a refactoring tool, not a starting point.
- Do not mark a sub-phase complete until `pytest --tb=short -q` passes and coverage is reported
- Coverage ≥ 90% per module — measured after each sub-phase, not deferred to hardening
- Code is not complete until tested with pass/fail evidence and coverage numbers in the session

### Review Cycle (MANDATORY after each sub-phase)
- Self-review all code while it is green: dead code, unused imports, over-abstraction, missing edge cases
- Fix all issues found before starting the next sub-phase
- Iterate review → fix until clean. There is no partial green.

### Documentation Discipline (ships with code — NO DEFERRAL)
- Update docs in the same task that adds user-visible capability or changes behaviour
- USAGE-GUIDE: update CLI reference, add new workflow sections
- LEARNING-GUIDE: add domain explanation for new concepts introduced
- SCORING-FORMULA: update whenever score inputs change
- V1-INPUT-TEMPLATE: update validation rules when input schema changes
- README: update Development Status and CLI table after each phase seal
- BENCHMARK-AUTHORING: update if benchmark conventions change

### Inherited Practices (from QEStrategyForge — verified, apply unchanged)
- `from __future__ import annotations` at top of every new module
- Type hints on all function signatures
- `@dataclass(slots=True)` for all data structures
- Path security: `Path.resolve()` + `is_relative_to(root)` for any user-supplied paths
- Protocol-based LLM client boundaries: `typing.Protocol` + `@runtime_checkable`
- Repo-local temp paths (`tmp/` gitignored); OS temp dirs are FORBIDDEN
- API keys from env vars ONLY — never from config files or defaults
- Error codes: 0=success, 1=IO error, 2=validation error, 3=generation error
- Binary benchmark assertions only (pass/fail); no weighted or partial scoring
- Composition root in CLI; inject dependencies as arguments — no module-level globals
- Minimal external dependencies: stdlib + PyYAML + click + openpyxl (add nothing without explicit decision)

## Decisions Made

### Program-level (inherited from QEStrategyForge, apply here)
- Each capability lives in its own repo with its own `claude-memory/` layer and `plan.md`.
- The top-level `Agentic Upskilling` workspace is the program-level planning hub.
- Validation uses binary pass/fail rules for setup, capability definition, MVP scope, build increments, and context recovery.
- Code follows KISS and reuse-first principles. No new abstractions unless the current slice truly needs them.
- Do not mark code complete until tested with reported pass/fail and coverage details.
- `claude-memory/`, `plan.md`, and `AGENTS.md` are public — part of the visible development workflow.
- License: AGPL-3.0-or-later.
- Slice completion requires evidence: tested code plus reported pass/fail and coverage details. TDD: red, green, refactor.
- Test temporary files use `tmp/` under the project root (gitignored). OS temp dirs (`tempfile.gettempdir()`) are fragile and forbidden.

### Optimization loop (inherited from QEStrategyForge Phase 10)
- Scoring: purely binary. Count of pass/fail checks across benchmarks. No weighted composites.
- Mutation strategy: cumulative within a run (mutate best-so-far); fresh baseline on new runs.
- Experiment tracking: `optimization_runs/` directory (gitignored). Config, scoreboard, per-iteration snapshots, mutation descriptors. Only winning prompts (`prompts/v2/`) committed.
- Winning prompts saved as `prompts/v2/`. User explicitly adopts by updating `prompt_builder.py`.
- Per-iteration wall-clock timeout: 300s default.

### Architecture (adapted from QEStrategyForge pattern)
- Core architecture: classify test metadata → scoring rules → prioritisation report.
  - Same classification → rules → rendering sequence as QEStrategyForge; domain is test suite health, not QE strategy.
- Deterministic core first. LLM integration only after the deterministic scoring and recommendation pipeline is proven on benchmarks.
- Input/output contracts (required report sections, required labels) must be fixed before any LLM integration begins.
- Machine-checkable output markers (required headings + required labels) are necessary for objective validation.
- Section-aware validation: labels must appear in the correct section, exactly once. Substring-only validation is insufficient.
- Heading validation must be line-anchored: `line.rstrip() == heading`, not `heading in markdown`.
- Prompt builder must receive every input schema field. Silent omission of fields from prompts is a hard-to-detect regression.
- Benchmark assertion runner pattern reused from QEStrategyForge. Same harness, domain-specific assertion content.

### Input / MVP
- Input for MVP: synthetic test metadata YAML. Real JUnit XML ingestion layered on after core scoring algorithm is proven.
- Cross-system reuse from QEStrategyForge: FlowResult, EXIT_* constants, benchmark_runner pattern, pyproject.toml structure, conftest.py pattern. Copy-adapt; do not rebuild.

## Product Definition
- **Problem:** Sprint delivery teams carry oversized regression suites that burn CI time and delay releases. Manual triage is ad-hoc and inconsistent. This tool analyses synthetic sprint + test-suite metadata to recommend which tests to run, defer, or retire for a given sprint, and to surface suite health signals.
- **Inputs:** YAML document with sprint context (stories, risk, changed areas, dependency stories), test suite (id, layer, coverage areas, execution time, flakiness, failure count), exploratory session notes, and constraints (budget, mandatory tags, flakiness thresholds).
- **Outputs:** Structured markdown report with 7 sections and 8 labelled summary values.
- **Non-goals (Phase 1):** JUnit XML ingestion, SCM integration, JIRA integration, LLM narrative, multi-hop deps, fuzzy area matching.

## Decisions Made (MVP — locked 2026-04-17)
- Scoring single weight: `risk`. `type` carries no scoring impact in Phase 1.
- Dependency traversal: 1-hop only.
- NFR elevation: any story with risk=high → all tests with layer=performance or layer=security are must-run overrides.
- Exploratory session notes are MVP input. Areas flagged by exploratory sessions amplify scores.
- Mandatory tags always produce must-run override regardless of score.
- Hard overrides (mandatory tag, NFR elevation) are exempt from the time budget.
- Budget overflow: lowest-scored scored-must-run test demotes to should-run; `Budget Overflow:` label set to Yes.
- Unique coverage is a global suite property: a test has unique coverage if ≥1 of its coverage_areas is not covered by any other test.
- Only automated tests with flakiness above threshold AND no unique coverage are retire candidates.
- Manual tests (automated: false): scored + tiered, excluded from budget calc, never in Retire Candidates, tagged `(manual)` in output.
- coverage_areas matching: exact string equality for Phase 1.
- Story `type` zero scoring impact in Phase 1 (carried for Phase 2+).
- Scoring weights hardcoded for Phase 1. No config file.

## Scoring Formula (locked)
```
raw_score = (10 × direct_coverage × risk_multiplier)
          + (5  × dep_coverage × dep_risk_multiplier)
          + (3  × exploratory_match)
          - (8  × flakiness_rate)

risk_multiplier:     high=1.0, medium=0.6, low=0.3
dep_risk_multiplier: same scale × 0.5
direct_coverage:     1 if any coverage_area ∩ story.changed_areas, else 0
dep_coverage:        1 if any coverage_area ∩ dep_story.changed_areas, else 0
explanatory_match:   1 if any coverage_area ∈ session risk_areas, else 0
```
Tier thresholds: must-run ≥ 8, should-run ≥ 4, defer < 4.

## Output Contract (locked)
Required headings (7, line-anchored):
- `## Optimisation Summary`
- `## Must-Run`
- `## Flaky Critical Coverage`
- `## Should-Run If Time Permits`
- `## Defer To Overnight Run`
- `## Retire Candidates`
- `## Suite Health Summary`

Required labels (8, section-aware):
- `Recommendation Mode:` → Optimisation Summary
- `Sprint Risk Level:` → Optimisation Summary
- `Total Must-Run:` → Optimisation Summary
- `Total Flaky Critical:` → Optimisation Summary
- `Total Retire Candidates:` → Optimisation Summary
- `NFR Elevation:` → Optimisation Summary
- `Budget Overflow:` → Optimisation Summary
- `Flakiness Tier High:` → Suite Health Summary

## Flaky-Critical Increment (locked 2026-04-23)
- Flaky-critical is a cross-cutting classification, not a scored tier.
- Qualification requires all of: flakiness above high threshold, direct overlap with sprint changed areas, matched story risk medium/high, and unique coverage.
- Flaky-critical tests are always executed, budget-exempt, and rendered in their own section.
- A single flaky-critical failure is not a clean release-gate signal; the report instructs operators to stabilize or replace the test.
- Optional input: `constraints.flaky_critical_rerun_max` with default `2`, valid range `1..5`.

## Active Next Work
- Flaky-critical elevation is fully shipped on `feature/flaky-critical-elevation` in 8 commits (original 5 feature commits + F5 prompt context + F3.3 CLI e2e + F4 docs).
- All drift items identified during post-feature review have been remediated: prompt rerun-max propagation (R1), doc config reconciliation (R2), stale source comments and authority-file updates (R3).
- Next action: PR preparation — squash decision, then open PR from `feature/flaky-critical-elevation` to `master`.

## Blockers
- None.

## Completed Milestones
- T1: Repo setup
- T2: Product definition
- T3: Python scaffold (11 tests)
- T4: Output contract / output_validator.py (21 tests)
- T5: input_loader.py (22 tests → 29 after review fixes)
- T6: context_classifier.py (17 tests)
- T7: scoring_engine.py (34 tests)
- T8: renderer.py + integration (18 tests → 19 after review fixes)
- T9: Benchmark YAMLs (3 scenarios x 2 files)
- T10: end_to_end_flow.py + benchmark_runner.py (11 tests)
- T11: cli.py with `iro run` and `iro benchmark` subcommands (14 tests)
- T12: Coverage hardening — all modules >=90%, total 99.10% (166 tests)
- Review fixes (Phase 1): temp-path compliance (repo_tmp fixture), input validation (name required, list-type checks), retire display (actual flakiness_rate)
- A1: `templates/test_suite_template.xlsx` — 13 columns, 5 example rows
- A2: `excel_loader.py` — strict required/optional validation, fuzzy headers, multi-sheet, passthrough columns
- A3: `iro import-tests` CLI subcommand — emits test_suite section only
- A5: Row+column validation for all required and typed optional cells
- A6: `benchmarks/sample-import.xlsx` + 62 Excel-related tests + 17 merge tests; 245 total
- A4: `iro run --tests <file> --sprint <file>` merge mode; `validate_raw()` extracted for reuse

