# Insights

Reusable lessons and engineering rules for the `intelligent-regression-optimizer` repository.

> **Update Policy:** Add entries when a lesson is likely to matter again in future sessions or related repos.
> **Scope:** Capability-specific but transferable.

---

## Carried over from QEStrategyForge (validated, apply here)

1. **Deterministic core first.** Build the deterministic scoring/rendering pipeline and prove it on benchmarks before any LLM layer touches it. LLM integration on top of a working deterministic pipeline is far safer than LLM-first.

2. **Binary benchmark assertions catch regressions faster than review.** Define assertion files before implementation. Check headings, labels, required substrings, and forbidden substrings.

3. **Section-aware output validation — not substring presence.** `label in output` passes even if the label is in the wrong section or duplicated. Section-aware checks (label appears once, in the correct section) are necessary for meaningful validation.

4. **Line-anchor heading validation.** Use `line.rstrip() == heading`, not `heading in markdown`. An LLM can embed a heading in prose or indent it; line-anchoring rejects both.

5. **Prompt builder must receive all input schema fields.** Silent omission of fields from prompts is a hard-to-detect regression — the LLM cannot produce context-correct output for fields it never sees. This happened in P12 with 7 fields missing for a full phase.

6. **Connector-first MVPs are a trap.** Early value is in algorithm quality, not in ingesting every format. Start with synthetic YAML, prove the scoring logic, then add JUnit XML ingestion.

7. **Input/output contract fixed before implementation.** Define required report sections and required labels before writing any scoring or rendering code. Changing the contract mid-build forces rework across validator, renderer, prompts, and benchmark assertions simultaneously.

8. **Self-improving loop quality depends on the evaluator.** The Karpathy loop only works if the scoring function is objective and binary. Subjective or weighted scoring makes the loop optimise for the wrong thing.

9. **Repo-local temp paths, never OS temp dirs.** `tempfile.gettempdir()` is fragile in sandboxed and CI environments. Use `tmp/` under the project root (gitignored).

10. **Classification → rules → rendering is the right architecture for decision-support tools.** It keeps output explainable and testable. For this repo: classify test metadata (flakiness, coverage overlap, execution time, failure history) → scoring rules → prioritisation report. Same pattern, different domain.

11. **Structural correctness is not the same as output quality.** A report that passes heading and label checks can still read as generic boilerplate. For a decision-support tool, the useful signal is how much the output varies with input context.

12. **Slice completion requires evidence, not just working behavior in one run.** Completion means tested code plus reported pass/fail and coverage details. No exceptions.

13. **Experiment tracking outside the committed tree.** `optimization_runs/` stays gitignored. Only winning prompt versions go into `prompts/v2/`. This keeps the commit history clean and reviewable.

14. **system_profile-equivalent dimensions consumed directly by the renderer need their own integration tests.** Rule-engine tests cannot catch renderer regressions on dimensions that bypass the decision dict. In this repo, any classifier dimension consumed directly by the report renderer must have an explicit integration test.

15. **Integration tests must cover the full escape path chain.** Unit tests on each module cannot catch coupling defects between classifier → rules → renderer → validator. A dedicated integration test file covering cross-module invariants is necessary.

16. **TDD is a hard constraint, not a style preference.** Writing the implementation before the test is a debt that compounds immediately. In this codebase: red → green → refactor, no exceptions. A sub-phase is not green until `pytest --tb=short -q` passes and coverage is reported.

17. **Review cycles prevent compounding debt better than end-of-phase cleanup.** A self-review after every sub-phase (dead code, edge cases, unused imports, over-abstraction) costs less than fixing accumulated issues after three sub-phases. Enforce it before moving to the next slice.

18. **Documentation deferred is documentation forgotten.** Shipping docs with the code that introduces the capability is the only reliable strategy. Retrospective documentation misses edge cases the implementer can still recall. Rule: if a task adds a CLI flag, a workflow, or a schema change — the affected doc file is updated in the same task.

19. **Copy-adapt over rebuild.** When QEStrategyForge has a proven module (LLM clients, config loader, client factory, benchmark runner), copy it and adapt the env prefix / domain names. Rebuilding from scratch introduces new bugs without adding new skills. The reuse decision is the default; divergence from QEStrategyForge requires a written reason.

20. **Coverage ≥ 90% per module is a module-level gate, not an aggregate.** A 95% project average can hide an 0%-covered new module. Measure coverage per module after each sub-phase and block progression if any module is below threshold.

21. **Help text, implementation, and tests form a contract triangle — all three must agree.** If any one diverges, the inconsistency lives invisibly. Stale help text that describes a `HEAD~1` default when the implementation requires explicit `--ref` misleads users and creates dead code. When adding a flag, write the help string, implementation, and at least one targeted test in the same commit.

22. **Carry warnings in the return type, not only in logs.** When a pipeline function discards warnings internally (e.g. `result, _ = merge_history(...)`), callers lose the ability to surface them to the user or assert on them in tests. Adding a `warnings: list[str]` field to `FlowResult` made the CLI, tests, and documentation all composable around warnings. Rule: if a function produces user-visible diagnostic information, put it in the return value, not just stderr.

23. **Scope reconciliation: narrow the documented contract before expanding the implementation.** When implementation delivers less than a plan promised (e.g. suite-level timestamps instead of testcase-level), the right first question is "can the narrowed scope satisfy users?" If yes, update the docs and plan to match the implementation — don't speculatively implement the harder case. Simpler implementation + honest docs beats ambitious docs + risky code.

24. **A behaviour-change benchmark must prove the recommendation shifts in both directions.** A benchmark that only shows history *causing* a retire recommendation proves history can demote tests — it doesn't prove history can *save* a test from incorrect retirement. Include one test per direction: YAML says safe but history says flaky → retire; YAML says flaky but history says stable → should-run. Both directions in one benchmark eliminates the possibility of a one-sided implementation.

25. **Pre-increment branch review is a mandatory gate, not optional polish.** Reviewing V1-A/V1-B before starting V1-C found 5 real gaps (silent override, contract mismatch, stale docs, missing benchmark, scope drift). Without the review those gaps would have become V1-C's inherited baseline. Rule: before starting the next increment, run a structured review of the current branch diff — implementation, tests, docs, governance — and produce written findings. Only start the next increment when the findings are resolved or explicitly deferred with reasons.

26. **Don't assume library API stability — verify the signature before writing tests.** `CliRunner(mix_stderr=False)` was valid in Click 8.1 but the constructor in Click 8.3 dropped it. Writing tests against an assumed API and discovering the failure only at runtime wastes a test-design iteration. Check `inspect.signature()` or the installed version before using unfamiliar constructor kwargs.

27. **Contract-ripple misses are the most persistent class of defect in this codebase.** When a contract (headings, labels, input schema fields) has N consumers (validator, renderer, prompt, tests, docs), updating the source of truth without updating all consumers creates silent drift. Manual review checklists are necessary but insufficient — they failed across two consecutive review rounds. The durable fix is a **contract-alignment guard test**: a test that programmatically imports the canonical contract (e.g. `output_validator.REQUIRED_HEADINGS`) and asserts that every downstream consumer (e.g. `system.txt`, assertion lists in other test files) agrees with it. This converts a review-dependent check into a CI-enforced tripwire. Rule: when adding or expanding a contract, also add a guard test that will break if any registered consumer falls out of sync.

28. **Every contract has a consumer registry — enumerate it before changing the contract.** The output contract is consumed by: `output_validator.py` (source of truth), `renderer.py`, `repair.py`, `prompts/v1/system.txt`, `test_template_loader.py`, `test_output_validator.py`, benchmark `.assertions.yaml` files, and docs (V1-OUTPUT-TEMPLATE, VALIDATION-HARNESS, USAGE-GUIDE, README). Maintaining an explicit list in AGENTS.md or memory prevents the "I updated the validator but forgot the prompt" class of error.

