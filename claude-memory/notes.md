# Notes

In-progress analysis, temporary notes, open questions, and working context for the `intelligent-regression-optimizer` repository.

> **Update Policy:** Use for temporary notes, unresolved questions, and short-lived working context.
> **Scope:** Capability-specific. Promote durable points into `memory.md` or `insights.md`.

---

## Open Questions
- None currently blocking.

## Deferred Items Log
- Real JUnit XML ingestion deferred until synthetic YAML deterministic core is proven.
- Fuzzy / hierarchical coverage_areas matching deferred to Phase 2 (SCM integration).
- SCM integration (actual changed files from git diff) deferred to Phase 2.
- JIRA integration deferred to Phase 3.
- LLM narrative layer deferred until deterministic pipeline is proven on all 3 benchmarks.
- Story `type`-based scoring deferred to Phase 2+.
- Multi-hop dependency traversal deferred to Phase 2.

## Working Notes
- CLI entry point: `iro` via pyproject.toml scripts. Subcommands: `run <input.yaml>`, `benchmark <assertions.yaml>`.
- Package name: `intelligent_regression_optimizer` (underscore). Tool name: `iro` (short).
- tmp/ is gitignored; use for test temp files, never OS tempdir.

