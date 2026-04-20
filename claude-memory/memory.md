# Memory

Current state, decisions, and active priorities for the `intelligent-regression-optimizer` capability.

> **Update Policy:** Update this file when the current capability direction, decisions, next actions, or blockers change.
> **Scope:** Capability-specific and durable across sessions for this repository.

---

## Capability Context
- Repository purpose: build an AI-native regression optimizer that analyses test suite history to identify redundant, flaky, and high-risk tests, then recommends prioritisation and pruning decisions to improve release confidence without increasing cycle time.
- Current stage: Phase 1 deterministic core COMPLETE. Phase 3 Excel adapter spike COMPLETE. Phase 2 documentation COMPLETE.
- Active branch: `phase-3-excel-adapter` (HEAD includes all Phase 1 + 3 + 2 work).

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
- **Outputs:** Structured markdown report with 6 sections and 7 labelled summary values.
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
Required headings (6, line-anchored):
- `## Optimisation Summary`
- `## Must-Run`
- `## Should-Run If Time Permits`
- `## Defer To Overnight Run`
- `## Retire Candidates`
- `## Suite Health Summary`

Required labels (7, section-aware):
- `Recommendation Mode:` → Optimisation Summary
- `Sprint Risk Level:` → Optimisation Summary
- `Total Must-Run:` → Optimisation Summary
- `Total Retire Candidates:` → Optimisation Summary
- `NFR Elevation:` → Optimisation Summary
- `Budget Overflow:` → Optimisation Summary
- `Flakiness Tier High:` → Suite Health Summary

## Active Next Work
- Phase 2 documentation (D1-D9) COMPLETE on `phase-3-excel-adapter`.
  - README.md rewritten (project overview, quick-start, CLI reference, doc index)
  - 8 doc files under `docs/`: V1-INPUT-TEMPLATE, V1-OUTPUT-TEMPLATE, DECISION-RULES, USAGE-GUIDE, SCENARIO-LIBRARY, VALIDATION-HARNESS, LEARNING-GUIDE, PHASED-IMPLEMENTATION
- Next: merge `phase-3-excel-adapter` → `main`; plan Phase 4+ if needed.

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
- A6: `benchmarks/sample-import.xlsx` + 62 Excel-related tests; 228 total

