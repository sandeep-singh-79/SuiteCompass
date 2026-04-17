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

