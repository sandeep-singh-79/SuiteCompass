# AGENTS.md - Workspace Instructions

The authoritative working context for this repository is maintained in:

- `claude-memory/memory.md`
- `claude-memory/insights.md`
- `claude-memory/notes.md`
- `plan.md`

Read these files before proceeding.

## Session Start Checklist

1. Read `AGENTS.md`
2. Read `claude-memory/memory.md`
3. Read `claude-memory/insights.md`
4. Read `claude-memory/notes.md`
5. Read `plan.md`
6. Confirm the active milestone, next action, and any blockers

## Working Rules

- This repo is the capability-specific workspace for `intelligent-regression-optimizer`.
- Keep this repo's memory focused on this capability.
- Use the top-level `Agentic Upskilling` memory layer for cross-program strategy and portfolio decisions.
- Update memory continuously during the session, not only at the end.
- Follow KISS: keep code simple and direct.
- Follow DRY: remove duplication when it becomes real and recurring.
- Follow YAGNI: do not build speculative flexibility ahead of current validated need.
- Follow SOLID where it helps clarity, testability, and change safety; do not force abstraction for its own sake.
- Prefer reuse and extension of existing code before introducing new modules or abstractions.
- Write new code only when it is genuinely required by the current slice or validation need.
- Refactor when complexity starts increasing or duplication becomes visible.
- All code must be tested before it is marked complete.
- Always report test pass/fail results and coverage details for code that was tested.
- Follow TDD in the standard order: red, green, refactor.

## Memory Update Discipline

- Update `claude-memory/memory.md` when the repo's current state, decisions, next actions, or blockers change.
- Update `claude-memory/insights.md` when a lesson is reusable across future sessions or related repos.
- Update `claude-memory/notes.md` for temporary notes and unresolved questions.
- Update `plan.md` as the active session or execution-cycle tracker.

## Validation Rules

Use binary pass/fail validation for capability work.

- Repo setup passes only if:
  - Git is initialized
  - `AGENTS.md`, `plan.md`, and `claude-memory/` exist
  - repo memory includes purpose, next work, and blockers

- Capability definition passes only if:
  - the problem statement is written in one clear paragraph
  - inputs are named
  - outputs are named
  - non-goals are named

- MVP scope passes only if:
  - one first user-visible flow is identified
  - success can be checked in pass/fail terms
  - the milestone is small enough to complete without building the whole platform

- Build increment passes only if:
  - expected behavior is stated before implementation
  - at least one pass/fail check exists
  - result is recorded in `claude-memory/notes.md` or `claude-memory/memory.md`
  - automated tests exist for normal, negative, and edge-case behavior where applicable

- Context recovery passes only if:
  - `AGENTS.md`, `claude-memory/`, and `plan.md` were reloaded
  - active milestone, next step, and blockers were restated before work continues

## Context Recovery Rule

Reload context from files when:
- context compacts
- a new session starts or the session relaunches
- there is a long gap
- priorities or plans change materially
- another agent or the user may have changed files
- the thread feels inconsistent with the files
- a major code, architecture, or repo-structure decision is about to be made

