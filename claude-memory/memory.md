# Memory

Current state, decisions, and active priorities for the `intelligent-regression-optimizer` capability.

> **Update Policy:** Update this file when the current capability direction, decisions, next actions, or blockers change.
> **Scope:** Capability-specific and durable across sessions for this repository.

---

## Capability Context
- Repository purpose: build an AI-native regression optimizer that analyses test suite history to identify redundant, flaky, and high-risk tests, then recommends prioritisation and pruning decisions to improve release confidence without increasing cycle time.
- Current stage: repo scaffolded. Product definition and MVP scope not yet written.
- This is the second business-capability repository in the broader Agentic Upskilling program.

## Decisions Made
- Input for MVP: synthetic test metadata YAML (not real CI history). Real JUnit XML ingestion is layered on after the core scoring algorithm is proven.
- Cross-system reuse from QEStrategyForge: FlowResult, EXIT_* constants, benchmark_runner pattern, pyproject.toml structure, conftest.py pattern. Copy-adapt; do not rebuild.
- Scoring must be purely binary (count of pass/fail checks). No weighted composites.
- Experiment tracking: `optimization_runs/` directory (.gitignored). Only winning prompts committed.

## Active Next Work
- Write product definition: problem statement, inputs, outputs, non-goals.
- Define MVP scope: first user-visible flow, binary success condition.
- Scaffold Python package structure.

## Blockers
- None. Repo just initialised.

