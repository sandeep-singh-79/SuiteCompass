"""Structural repair for LLM-generated markdown reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from intelligent_regression_optimizer.models import TierResult
from intelligent_regression_optimizer.output_validator import (
    LABEL_SECTION_MAP,
    REQUIRED_HEADINGS,
    REQUIRED_LABELS,
    _parse_sections,
)


@dataclass
class RepairResult:
    markdown: str
    actions: list[str] = field(default_factory=list)
    is_repaired: bool = False


def _label_value(label: str, tier_result: TierResult, classifications: dict[str, Any]) -> str:
    """Return a sensible fallback value for a missing or misplaced label."""
    if label == "Recommendation Mode:":
        return "Recommendation Mode: llm-repaired"
    if label == "Sprint Risk Level:":
        return f"Sprint Risk Level: {classifications.get('sprint_risk_level', 'unknown')}"
    if label == "Total Must-Run:":
        return f"Total Must-Run: {len(tier_result.must_run)}"
    if label == "Total Retire Candidates:":
        return f"Total Retire Candidates: {len(tier_result.retire)}"
    if label == "NFR Elevation:":
        val = "Yes" if classifications.get("nfr_elevation_required") else "No"
        return f"NFR Elevation: {val}"
    if label == "Budget Overflow:":
        val = "Yes" if tier_result.budget_overflow else "No"
        return f"Budget Overflow: {val}"
    if label == "Flakiness Tier High:":
        return "Flakiness Tier High: 0 tests above threshold"
    return f"{label} (repaired)"


def _inject_after_heading(markdown: str, heading: str, value: str) -> str:
    """Insert value on the line immediately following the given heading."""
    lines = markdown.splitlines()
    new_lines = []
    for line in lines:
        new_lines.append(line)
        if line.rstrip() == heading:
            new_lines.append(value)
    return "\n".join(new_lines)


def repair_output(
    markdown: str,
    tier_result: TierResult,
    classifications: dict[str, Any],
) -> RepairResult:
    """Attempt structural repair of LLM-generated markdown.

    Strategies applied in order:
    1. Inject missing required headings.
    2. For each required label: if absent, misplaced, or duplicated — remove all
       occurrences and re-inject once in the correct section.
    3. Fix Recommendation Mode to 'llm-repaired' if any repair was made.
    """
    actions: list[str] = []
    had_trailing_newline = markdown.endswith("\n")

    # --- 1. Inject missing headings -----------------------------------------
    present_headings = {line.rstrip() for line in markdown.splitlines() if line.rstrip() in REQUIRED_HEADINGS}
    for heading in REQUIRED_HEADINGS:
        if heading not in present_headings:
            markdown = markdown.rstrip("\n") + f"\n\n{heading}\n\n"
            actions.append(f"Injected missing heading: {heading!r}")

    # --- 2. Fix each label (absent / misplaced / duplicate) -----------------
    for label in REQUIRED_LABELS:
        target_section = LABEL_SECTION_MAP[label]
        sections = _parse_sections(markdown)

        in_correct = label in sections.get(target_section, "")
        in_wrong = [h for h, body in sections.items() if h != target_section and label in body]
        count_in_correct = sections.get(target_section, "").count(label)

        if in_correct and not in_wrong and count_in_correct == 1:
            continue  # already correct and unique — nothing to do

        # Remove all occurrences, then re-inject once in the correct section
        lines = [line for line in markdown.splitlines() if label not in line]
        markdown = "\n".join(lines)

        if not in_correct and not in_wrong:
            actions.append(f"Injected missing label: {label!r}")
        elif in_wrong and not in_correct:
            actions.append(f"Moved misplaced label to correct section: {label!r}")
        else:  # duplicate (in correct + wrong, or multiple in correct)
            actions.append(f"Duplicate label removed: {label!r}")

        markdown = _inject_after_heading(markdown, target_section, _label_value(label, tier_result, classifications))

    # --- 3. Fix Recommendation Mode if any repair was applied ---------------
    if actions:
        lines = markdown.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("Recommendation Mode:"):
                lines[i] = "Recommendation Mode: llm-repaired"
                break
        markdown = "\n".join(lines)

    if had_trailing_newline and not markdown.endswith("\n"):
        markdown += "\n"

    return RepairResult(markdown=markdown, actions=actions, is_repaired=bool(actions))

