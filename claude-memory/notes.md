# Notes

In-progress analysis, temporary notes, open questions, and working context for the `intelligent-regression-optimizer` repository.

> **Update Policy:** Use for temporary notes, unresolved questions, and short-lived working context.
> **Scope:** Capability-specific. Promote durable points into `memory.md` or `insights.md`.

---

## Open Questions
- None. MVP sealed.

## Backlogged Items (not planned)
- Real JUnit XML ingestion
- Fuzzy / hierarchical coverage_areas matching
- SCM integration (git diff → changed_areas)
- Jira auto-populate sprint_context.stories
- LLM narrative layer
- Story `type`-based scoring
- Multi-hop dependency traversal
- CI pipeline (GitHub Actions)
- PyPI publish

These are permanently deferred unless the program revisits this capability.

## Working Notes
- CLI entry point: `iro` via pyproject.toml scripts. Subcommands: `run <input.yaml>`, `run --tests <t.yaml> --sprint <s.yaml>`, `benchmark <input.yaml> <assertions.yaml>`, `import-tests <file.xlsx>`.
- Package name: `intelligent_regression_optimizer` (underscore). Tool name: `iro` (short).
- `tests/.tmp/` is gitignored; `repo_tmp` fixture creates per-test subdirectories there. Never OS tempdir.
- `import-tests` emits `test_suite:` block only. User can merge with sprint YAML manually OR use `iro run --tests --sprint`.
- Passthrough columns (priority, external_id, owner, module) are carried to YAML output but ignored by the scoring engine.

