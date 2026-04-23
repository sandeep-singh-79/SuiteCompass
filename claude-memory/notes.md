# Notes

In-progress analysis, temporary notes, open questions, and working context for the `intelligent-regression-optimizer` repository.

> **Update Policy:** Use for temporary notes, unresolved questions, and short-lived working context.
> **Scope:** Capability-specific. Promote durable points into `memory.md` or `insights.md`.

---

## Open Questions
- None.

## Sealed — v1.1.0 (2026-04-23)
- All review findings from rounds 1–3 resolved and shipped.
- PR #5 merged (squashed single commit `c10a878`), branch deleted, tag `v1.1.0` pushed.
- 605 tests, 22 benchmarks, 0 failures.
- No open drift, no deferred findings.

## Pre-Seal Review Findings (2026-04-22) — RESOLVED
- Scope reviewed: V1-C implementation and recent hardening changes, judged against plan.md as authority.
- Deterministic V1-A/V1-B behavior remains green: targeted review suite 111 passed; full suite 542 passed.
- All 6 blocking tracks (R1-R6) resolved in remediation session (2026-04-22):
	- R1 (provider exceptions exit 0 via fallback): DONE
	- R2 (--summary-only mode): DONE
	- R3 (prompt override reasons + history provenance): DONE
	- R4 (min_section_word_count narrative assertions): DONE
	- R5 (vacuous or-True assertion fixed): DONE
	- R6 (plan/docs reconciled — llm_assisted → llm, SUITECOMPASS → IRO, exit-3 removed): DONE
- Full-suite gate passed after remediation: 562 tests, 96.47% coverage.
- Follow-up review found two remaining drift issues and they were corrected in the same session:
	- README and USAGE-GUIDE exit-code tables no longer advertise exit 3 for LLM provider exceptions.
	- LEARNING-GUIDE diff-areas examples now include the required `--ref HEAD~1` argument.
- Next: merge/tag or final acceptance review before release.

## Coverage Notes (V1-A sealed)
Known unreachable/pre-existing lines that don't warrant tests:
- `junit_xml_parser.py` line 116: `_compute_flakiness_rate` `total == 0` guard — unreachable from public API (accumulator never produces empty entry lists)
- `end_to_end_flow.py` line 172: `EXIT_VALIDATION_ERROR` from `_run_from_package` — requires renderer to emit invalid markdown; not possible with normal inputs
- `context_classifier.py` line 89: pre-existing partial branch from before V1-A
- `input_loader.py` line 102: pre-existing line from before V1-A
- `excel_loader.py`: pre-existing gaps from before V1-A

## v1.0 Active Phase Tracker

| Sub-phase | Description | Status |
|---|---|---|
| A1 | TestHistoryRecord model + history_loader.py (CSV/JSON) | Complete — 38 tests, 97%/98% coverage, V1-INPUT-TEMPLATE updated |
| A2 | JUnit XML parser (junit_xml_parser.py, stdlib ElementTree) | Complete — 21 tests, 100% coverage, LEARNING-GUIDE updated |
| A3 | merge_history() + pipeline wiring in end_to_end_flow.py | Complete — 15 new tests, end_to_end_flow 97% coverage |
| A4 | --history-dir / --history-file CLI flags + benchmark | Complete — 10 new tests, cli.py 94% coverage |
| A5 | Phase A hardening (coverage ≥ 90%, regression check) | Complete — 343 tests, 98.40% coverage, cli.py/history_loader.py at 100% |
| B1 | area-map.yaml config + diff_mapper.py (fnmatch) | Complete — 35 tests, 100% coverage, commit 095bddc |
| B2 | iro diff-areas subcommand + iro run integration | Complete — 394 tests (19 new), 97.18% coverage, commit 9fedd32 |
| B3 | Phase B hardening | Complete — area-map.yaml template, USAGE-GUIDE Workflows 4+5, V1-INPUT-TEMPLATE area-map schema, commit 58e2542 |
| C1 | LLM client infra copy-adapt from QEStrategyForge | Complete — llm_client, openai/ollama/gemini clients, config_loader, client_factory |
| C2 | prompt_builder.py + prompts/v1/ templates | Complete — template_loader, 5 prompt templates, prompt_builder with scenario routing |
| C3 | llm_flow.py + repair/fallback + comparison.py | Complete — llm_flow, repair (4 strategies), comparison reporter |
| C4 | --mode / --provider / --model CLI flags + live tests | Complete — 7 new CLI flags, LLM routing in run command |
| C5 | Phase C hardening + LLM benchmark | Not started |
| Seal | Version 1.0.0 bump, README, PHASED-IMPLEMENTATION retro, tag | Not started |

## v1.0 Backlogged Items (not in scope for v1.0)
- CI webhook listener (after V1-B proves file-level mapping)
- Multi-hop dependency traversal
- Fuzzy coverage_areas matching
- PyPI publish
- Configurable scoring weights
- Karpathy optimization loop for SuiteCompass prompts
- AST-level / method-level change detection
- Jira auto-populate sprint_context.stories
- Story `type`-based scoring (carried forward, zero scoring impact through v1.0)

## Working Notes
- CLI entry point: `iro` via pyproject.toml scripts. Subcommands: `run <input.yaml>`, `run --tests <t.yaml> --sprint <s.yaml>`, `benchmark <input.yaml> <assertions.yaml>`, `import-tests <file.xlsx>`.
- Package name: `intelligent_regression_optimizer` (underscore). Tool name: `iro` (short).
- `tests/.tmp/` is gitignored; `repo_tmp` fixture creates per-test subdirectories there. Never OS tempdir.
- `import-tests` emits `test_suite:` block only. User can merge with sprint YAML manually OR use `iro run --tests --sprint`.
- Passthrough columns (priority, external_id, owner, module) are carried to YAML output but ignored by the scoring engine.

