"""LLM pipeline orchestration: prompt → generate → validate → repair → fallback."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from intelligent_regression_optimizer.llm_client import LLMClient
from intelligent_regression_optimizer.models import (
    EXIT_OK,
    FlowResult,
    GenerationRequest,
    TierResult,
)
from intelligent_regression_optimizer.output_validator import validate_output
from intelligent_regression_optimizer.prompt_builder import build_prompt
from intelligent_regression_optimizer.repair import repair_output


@dataclass
class LLMFlowResult:
    """Extended result carrying repair and fallback metadata."""

    flow_result: FlowResult
    recommendation_mode: str           # "llm" | "llm-repaired" | "deterministic-fallback"
    raw_llm_output: str | None
    repair_actions: list[str] = field(default_factory=list)


def run_llm_pipeline(
    normalized: dict[str, Any],
    classifications: dict[str, Any],
    tier_result: TierResult,
    client: LLMClient,
) -> LLMFlowResult:
    """Full LLM pipeline: prompt → generate → validate → repair → fallback.

    Steps:
    1. Build prompt from normalized/classifications/tier_result.
    2. Call client.generate().
    3. Validate raw LLM output.
    4. If invalid: attempt structural repair, re-validate.
    5. If still invalid: fall back to deterministic renderer.
    Returns LLMFlowResult with appropriate recommendation_mode.
    """
    # Step 1: build prompt
    system_prompt, user_prompt = build_prompt(normalized, classifications, tier_result)

    request = GenerationRequest(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    # Step 2: generate
    try:
        response = client.generate(request)
    except Exception as exc:  # noqa: BLE001
        fallback_md = _deterministic_fallback(normalized, classifications, tier_result)
        return LLMFlowResult(
            flow_result=FlowResult(exit_code=EXIT_OK, message=fallback_md, output_path=None),
            recommendation_mode="deterministic-fallback",
            raw_llm_output=None,
            repair_actions=[f"Provider error: {exc}"],
        )

    raw_output = response.content

    # Step 3: validate raw output
    validation = validate_output(raw_output)
    if validation.is_valid:
        return LLMFlowResult(
            flow_result=FlowResult(exit_code=EXIT_OK, message=raw_output, output_path=None),
            recommendation_mode="llm",
            raw_llm_output=raw_output,
        )

    # Step 4: repair
    repair_result = repair_output(raw_output, tier_result, classifications)
    repaired_validation = validate_output(repair_result.markdown)
    if repaired_validation.is_valid:
        return LLMFlowResult(
            flow_result=FlowResult(exit_code=EXIT_OK, message=repair_result.markdown, output_path=None),
            recommendation_mode="llm-repaired",
            raw_llm_output=raw_output,
            repair_actions=repair_result.actions,
        )

    # Step 5: deterministic fallback
    fallback_md = _deterministic_fallback(normalized, classifications, tier_result)
    return LLMFlowResult(
        flow_result=FlowResult(exit_code=EXIT_OK, message=fallback_md, output_path=None),
        recommendation_mode="deterministic-fallback",
        raw_llm_output=raw_output,
        repair_actions=repair_result.actions,
    )


def _deterministic_fallback(
    normalized: dict[str, Any],
    classifications: dict[str, Any],
    tier_result: TierResult,
) -> str:
    """Render a deterministic report and patch the Recommendation Mode label."""
    from intelligent_regression_optimizer.renderer import render_report
    md = render_report(normalized, classifications, tier_result)
    return md.replace(
        "Recommendation Mode: deterministic",
        "Recommendation Mode: deterministic-fallback",
        1,
    )
