# Phased Implementation

Architecture retrospective and decision log for SuiteCompass. What was built in each phase, why key decisions were made, and what's planned next.

---

## Phase 1 — Deterministic Core

**Branch:** `phase-1-deterministic-core`
**Duration:** Initial build through T1–T12
**Deliverables:** Complete deterministic scoring and reporting pipeline

### What Was Built

| Module | Purpose |
|---|---|
| `models.py` | Data structures: InputPackage, ScoredTest, TierResult, FlowResult, ValidationResult |
| `input_loader.py` | YAML loading + validation (required fields, types, value ranges, dependency resolution) |
| `context_classifier.py` | Derive 5 classification dimensions from normalised input |
| `rule_engine.py` | Score every test, identify retire candidates, apply overrides, budget constraint |
| `renderer.py` | Render 6-section markdown report with 7 machine-checkable labels |
| `output_validator.py` | Validate rendered report against output contract |
| `end_to_end_flow.py` | Wire complete pipeline: load → classify → score → render → validate |
| `benchmark_runner.py` | Run assertions against rendered output (4 assertion types) |
| `cli.py` | Click-based CLI: `iro run`, `iro benchmark` |
| 3 benchmark scenarios | high-risk-feature-sprint, low-risk-bugfix-sprint, degraded-suite-high-flakiness |

### Key Architecture Decisions

**Classification → Rules → Rendering pipeline**
- Same pattern as QEStrategyForge. Keeps output explainable and testable.
- Each stage has a clear contract: input → output dict → next stage.

**Deterministic-first, LLM-later**
- No LLM integration in Phase 1. The scoring formula is entirely deterministic.
- Rationale: prove the algorithm on benchmarks before adding unpredictable generation.

**Fixed output contract before implementation**
- 6 headings and 7 labels were defined before any code was written.
- Changing the contract mid-build would force rework across validator, renderer, and assertions.

**Binary benchmark assertions**
- All validation is pass/fail. No weighted scores, no subjective quality measures.
- This makes regressions detectable by machines, not just humans.

**1-hop dependency traversal**
- Deliberately limited. Multi-hop adds complexity without clear value for typical sprint shapes.
- Can be extended in Phase 2+ if real-world usage demonstrates the need.

**Scoring formula locked**
- Weights are hardcoded (10, 5, 3, -8). No configuration file.
- Rationale: configuration implies choice; choice requires guidance. For Phase 1, a single well-tuned formula is more useful than a configurable one.

### Metrics

- 166 tests, 99.10% coverage
- All 3 benchmarks green
- All modules ≥ 90% coverage individually

### Lessons Learned

1. Section-aware validation catches bugs substring-only validation misses (a label in the wrong section still "passes" with substring matching).
2. Line-anchored heading validation prevents false positives from headings embedded in prose.
3. `conftest.py` fixtures (like `repo_tmp`) applied project-wide enforce standards without per-test boilerplate.

---

## Phase 3 — Excel Import Adapter (Spike)

**Branch:** `phase-3-excel-adapter` (extends `phase-1-deterministic-core`)
**Scope:** A1–A3, A5, A6 (A4 merge utility deferred)
**Deliverables:** Excel template, Excel loader, CLI `import-tests` subcommand

### Why Phase 3 Before Phase 2

Phase 3 was prioritised over Phase 2 (documentation) because:
- It adds concrete functionality that documentation should reference
- It validates the input schema against a real-world format (Excel)
- Phase 2 docs benefit from covering the complete tool surface (including Excel import)

### What Was Built

| Component | Purpose |
|---|---|
| `templates/test_suite_template.xlsx` | 13-column Excel template with 5 example rows + Instructions sheet |
| `excel_loader.py` | Load .xlsx → validate → produce test dicts matching input schema |
| `cli.py` `import-tests` | New subcommand: emit `test_suite:` YAML block from Excel |
| `benchmarks/sample-import.xlsx` | 7-row benchmark sample for round-trip testing |
| 62 Excel-related tests | Loader, CLI, round-trip tests |

### Key Design Decisions

**Test_suite section only (no stubs)**
- `import-tests` emits only the `test_suite:` block, not a full input file with placeholders.
- Rationale: emitting placeholder `sprint_context` would create an unsafe "successful" run path where users accidentally run on fake data.

**Strict validation (fail fast)**
- Blank required cells raise immediately (not silently produce defaults).
- Malformed typed optional cells raise (not silently coerce).
- Rationale: silent coercion produces incorrect optimizer input without user visibility.

**Fuzzy column matching**
- Headers are normalised (lowercase, strip spaces/parens/underscores/hyphens) and matched against an alias table.
- Supports common variations: "Execution Time (secs)", "exec_time", "duration_in_seconds", etc.

**Passthrough columns**
- 4 optional columns (Priority, External ID, Owner, Module) are imported and carried to YAML but not scored.
- Rationale: teams always have this metadata; carrying it positions for future use without affecting current scoring.

**Multi-sheet support**
- Auto-selects sheet named "Tests" (case-insensitive), falls back to first sheet, `--sheet` flag overrides.

### Review Findings and Fixes

Two GPT-5.4 reviews identified critical issues that were fixed:

| Finding | Fix |
|---|---|
| Silent coercion of blank required cells | Added explicit blank checks before type conversion |
| Silent coercion of malformed optional cells | Changed from try/except swallowing to explicit raise |
| CLI emitted full stub (plan mismatch) | Removed stubs; emit test_suite only |
| Unused import | Removed `get_column_letter` |
| Governance drift | Updated plan.md and claude-memory to reflect delivery |

### Metrics

- 228 tests total (62 Excel-specific), all green
- 98%+ coverage
- All prior Phase 1 benchmarks still pass

---

## Phase 2 — Documentation

**Branch:** `phase-3-excel-adapter` (extended in place)
**Deliverables:** D1–D9 documentation files

### What Was Built

| Doc | Purpose |
|---|---|
| `README.md` | Project overview, quick-start, CLI reference, documentation index |
| `docs/V1-INPUT-TEMPLATE.md` | Full input schema with field-level annotations |
| `docs/V1-OUTPUT-TEMPLATE.md` | Annotated output contract with sample report |
| `docs/DECISION-RULES.md` | Complete scoring, tiering, override, and retire logic |
| `docs/USAGE-GUIDE.md` | End-to-end workflows (YAML-first and Excel import) |
| `docs/SCENARIO-LIBRARY.md` | 7 named scenarios with expected behaviour |
| `docs/VALIDATION-HARNESS.md` | Benchmark system guide |
| `docs/LEARNING-GUIDE.md` | Tutorial: regression prioritisation thinking (6 sections + 5 exercises) |
| `docs/PHASED-IMPLEMENTATION.md` | This file — architecture retrospective |

### Key Decisions

- No code changes during Phase 2 — documentation only
- QEStrategyForge documentation style used as template for structure and depth
- All docs cross-linked from README documentation index
- Sample output generated live from `iro run tests/fixtures/valid_input.yaml`

---

## Architecture Decision Log

| Decision | Rationale | Phase |
|---|---|---|
| Deterministic scoring, no LLM | Prove algorithm on benchmarks before adding generation unpredictability | 1 |
| Classification → Rules → Rendering | Keeps output explainable; each stage independently testable | 1 |
| Fixed output contract before code | Prevents mid-build rework across validator, renderer, assertions | 1 |
| Scoring formula hardcoded | No config file — single well-tuned formula more useful than configurable one | 1 |
| 1-hop dependency only | Multi-hop complexity unjustified for typical sprint shapes | 1 |
| Binary validation only | Machines detect regressions faster than humans with pass/fail | 1 |
| Excel strict validation | Silent coercion produces incorrect input; fail fast preferred | 3 |
| test_suite only output | Full stubs create unsafe success path with placeholder data | 3 |
| Passthrough columns | Positions for future scoring without affecting current pipeline | 3 |
| Phase 3 before Phase 2 | Docs benefit from covering complete tool surface including Excel | 3 |

---

## What's Next (Phase 4+)

| Phase | Scope | Trigger |
|---|---|---|
| Phase 4 | Jira adapter — auto-populate sprint_context from sprint board | When adoption justifies API integration |
| Phase 5 | JUnit XML adapter — derive flakiness_rate and failure_count from historical test runs | When teams need automated enrichment |
| Phase 6 | LLM narrative layer — generate explanatory text alongside deterministic recommendations | When deterministic pipeline is proven in production use |
| Phase 7 | Multi-hop dependency traversal | When real-world usage demonstrates 1-hop insufficient |
| Phase 8 | Fuzzy area matching (SCM-derived changed_areas) | When SCM integration available |
| Phase 9 | Configurable scoring weights | When different teams need different multipliers |
