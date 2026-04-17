# Insights

Reusable lessons and engineering rules for the `intelligent-regression-optimizer` repository.

> **Update Policy:** Add entries when a lesson is likely to matter again in future sessions or related repos.
> **Scope:** Capability-specific but transferable.

---

## From QEStrategyForge (carry-forward)
- Build the deterministic core first. LLM integration on top of a working deterministic pipeline is far safer than building LLM-first.
- Binary benchmark assertions catch regressions faster than subjective review. Define them before any LLM layer touches the output.
- Section-aware output validation (not just substring presence) catches placement defects that substring checks miss.
- Prompt builder must receive all input schema fields. Silent omission of fields from prompts is a hard-to-detect regression.
- Line-anchor heading validation: `line.rstrip() == heading` not `heading in markdown`.
- `system_profile` and similar classification dimensions consumed directly by the renderer (not via decisions) need their own explicit integration tests — rule-engine tests cannot catch renderer regressions on those paths.

