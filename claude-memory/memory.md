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

## Active Next Work
- Write product definition: problem statement, inputs, outputs, non-goals.
- Define MVP scope: first user-visible flow, binary success condition.
- Scaffold Python package structure.

## Blockers
- None. Repo just initialised.

