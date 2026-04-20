# Session Plan

> **Purpose:** Track the active planning and execution steps for the `intelligent-regression-optimizer` repository.
> **Scope:** Session-specific or cycle-specific. Refresh as milestones move.
> **Last Updated:** 2026-04-17

---

## Session Details

| Field | Value |
|---|---|
| Capability | intelligent-regression-optimizer |
| Objective | Implement deterministic MVP — 3 benchmarks green, ≥110 tests, all modules ≥90% coverage |
| Current Phase | Phase 1 — Implementation |
| Current Focus | T3 Python scaffold |
| Last Updated | 2026-04-17 |

---

## Plan Tracks (TDD: red → green → refactor)

| Track | Goal | Status | Notes |
|---|---|---|---|
| T1 - Repo Setup | Git init, memory layer, AGENTS.md, plan.md | Complete | |
| T2 - Product Definition | Problem statement, inputs, outputs, non-goals | Complete | Locked 2026-04-17 |
| T3 - Python Scaffold | pyproject.toml, src layout, models.py | In Progress | tests RED first |
| T4 - Output Contract | output_validator.py + test (≥15) | Not Started | parallel with T5 |
| T5 - Input Loader | input_loader.py + test (≥15) | Not Started | parallel with T4 |
| T6 - Context Classifier | context_classifier.py + test (≥12) | Not Started | depends T5 |
| T7 - Scoring Engine | scoring_engine.py + test (≥22) | Not Started | depends T6 |
| T8 - Renderer | renderer.py + test (≥12) | Not Started | depends T7 |
| T9 - Benchmarks | 3x input + assertions YAMLs | Not Started | after T4 |
| T10 - E2E Flow | end_to_end_flow.py, benchmark_runner.py | Not Started | depends T8+T9 |
| T11 - CLI | cli.py + test (≥8) | Not Started | depends T10 |
| T12 - Hardening | all modules ≥90%, all benchmarks green | Not Started | depends T11 |

---

## MVP Acceptance Criteria (all must pass)

1. 3 benchmark assertion files pass via `benchmark_runner`
2. All modules ≥90% coverage
3. ≥110 tests passing
4. `output_validator.validate_output()` passes for every benchmark output
5. CLI `iro run` returns exit 0 for valid input, exit 2 for invalid
6. CLI `iro benchmark` returns exit 0 for passing assertions, exit 1 for failing

---

## Dependency Graph

```
T3 (scaffold) -+-> T4 (output contract) --------------------------> T9 (benchmarks)
               |                                                          |
               +-> T5 (input loader) -> T6 (classifier) -> T7 (scorer) -> T8 (renderer)
                                                                          |
                                   T9 -----------------------------------+
                                                                          v
                                                               T10 (E2E + contracts)
                                                                          |
                                                               T11 (CLI) -> T12
```

T4 and T5 run in parallel after T3. T9 starts after T4. T6->T7->T8 sequential.
