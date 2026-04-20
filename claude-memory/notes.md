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
- Jira auto-populate sprint_context.stories deferred to Phase 4+ (not scoped).
- LLM narrative layer deferred until deterministic pipeline is proven on all 3 benchmarks.
- Story `type`-based scoring deferred to Phase 2+.
- Multi-hop dependency traversal deferred to Phase 2.

## Working Notes
- CLI entry point: `iro` via pyproject.toml scripts. Subcommands: `run <input.yaml>`, `run --tests <t.yaml> --sprint <s.yaml>`, `benchmark <input.yaml> <assertions.yaml>`, `import-tests <file.xlsx>`.
- Package name: `intelligent_regression_optimizer` (underscore). Tool name: `iro` (short).
- `tests/.tmp/` is gitignored; `repo_tmp` fixture creates per-test subdirectories there. Never OS tempdir.
- `import-tests` emits `test_suite:` block only. User can merge with sprint YAML manually OR use `iro run --tests --sprint`.
- Passthrough columns (priority, external_id, owner, module) are carried to YAML output but ignored by the scoring engine.

