"""Comparison reporter — side-by-side deterministic vs LLM output."""
from __future__ import annotations

from intelligent_regression_optimizer.llm_flow import LLMFlowResult


def build_comparison_report(deterministic_md: str, llm_flow_result: LLMFlowResult) -> str:
    """Build a comparison markdown report with deterministic and LLM outputs side by side."""
    repair_count = len(llm_flow_result.repair_actions)
    lines: list[str] = []

    lines.append("## Comparison Summary")
    lines.append("")
    lines.append(f"LLM Recommendation Mode: {llm_flow_result.recommendation_mode}")
    lines.append(f"Repairs Applied: {repair_count}")
    lines.append("")

    lines.append("## Deterministic Output")
    lines.append("")
    lines.append(deterministic_md)
    lines.append("")

    lines.append("## LLM Output")
    lines.append("")
    lines.append(llm_flow_result.flow_result.message)
    lines.append("")

    if llm_flow_result.repair_actions:
        lines.append("## Repair Log")
        lines.append("")
        for action in llm_flow_result.repair_actions:
            lines.append(f"- {action}")
        lines.append("")

    return "\n".join(lines)
