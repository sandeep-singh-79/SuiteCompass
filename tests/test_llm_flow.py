"""Tests for LLM flow orchestration."""
from __future__ import annotations

import pytest

from intelligent_regression_optimizer.llm_client import FakeLLMClient
from intelligent_regression_optimizer.models import (
    EXIT_GENERATION_ERROR,
    EXIT_OK,
    GenerationRequest,
    GenerationResponse,
    ProviderConfig,
    ScoredTest,
    TierResult,
)
from intelligent_regression_optimizer.llm_flow import LLMFlowResult, run_llm_pipeline
from intelligent_regression_optimizer.output_validator import validate_output


def _make_tier_result() -> TierResult:
    return TierResult(
        must_run=[ScoredTest("T-01", "Login", 9.0, "must-run", False, None, False)],
    )


def _make_classifications() -> dict:
    return {
        "sprint_risk_level": "medium",
        "suite_health": "stable",
        "time_pressure": "moderate",
        "nfr_elevation_required": False,
        "per_test_stability": {},
    }


def _base_normalized() -> dict:
    return {
        "sprint_context": {"sprint_name": "S42", "stories": []},
        "test_suite": [{"id": "T-01", "name": "Login", "execution_time_secs": 60}],
        "constraints": {"time_budget_mins": 60, "flakiness_high_tier_threshold": 0.20},
    }


# ---------------------------------------------------------------------------
# Happy path — valid LLM output
# ---------------------------------------------------------------------------

def test_happy_path_returns_llm_mode():
    client = FakeLLMClient()  # returns valid report with "Recommendation Mode: llm"
    result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), client)
    assert isinstance(result, LLMFlowResult)
    assert result.recommendation_mode == "llm"
    assert result.repair_actions == []
    assert result.flow_result.exit_code == EXIT_OK


def test_happy_path_output_passes_contract():
    client = FakeLLMClient()
    result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), client)
    assert validate_output(result.flow_result.message).is_valid


def test_happy_path_raw_llm_output_preserved():
    client = FakeLLMClient()
    result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), client)
    assert result.raw_llm_output is not None
    assert len(result.raw_llm_output) > 0


# ---------------------------------------------------------------------------
# Repair path — invalid but repairable LLM output
# ---------------------------------------------------------------------------

def _make_repairable_output() -> str:
    """Valid report with one missing label — repairable."""
    return (
        "## Optimisation Summary\n\n"
        "Recommendation Mode: llm\n"
        "Sprint Risk Level: medium\n"
        # Total Must-Run missing — will be repaired
        "Total Retire Candidates: 0\n"
        "NFR Elevation: No\n"
        "Budget Overflow: No\n\n"
        "## Must-Run\n\n"
        "- T-01 Login (score: 9.0)\n\n"
        "## Should-Run If Time Permits\n\n"
        "_No tests in this tier._\n\n"
        "## Defer To Overnight Run\n\n"
        "_No tests in this tier._\n\n"
        "## Retire Candidates\n\n"
        "_No retire candidates._\n\n"
        "## Suite Health Summary\n\n"
        "Flakiness Tier High: 0 tests above threshold\n"
    )


def test_repair_path_returns_llm_repaired_mode():
    client = FakeLLMClient(response_content=_make_repairable_output())
    result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), client)
    assert result.recommendation_mode == "llm-repaired"
    assert len(result.repair_actions) > 0


def test_repair_path_output_passes_contract():
    client = FakeLLMClient(response_content=_make_repairable_output())
    result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), client)
    assert validate_output(result.flow_result.message).is_valid


def test_repair_path_raw_output_preserved():
    client = FakeLLMClient(response_content=_make_repairable_output())
    result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), client)
    assert result.raw_llm_output == _make_repairable_output()


# ---------------------------------------------------------------------------
# Fallback path — unrepairable LLM output
# ---------------------------------------------------------------------------

def _make_unrepairable_output() -> str:
    """Completely wrong structure — used with patched repair to test fallback path."""
    return "This is not a valid report at all."


def test_fallback_path_returns_deterministic_fallback_mode():
    from unittest.mock import patch
    from intelligent_regression_optimizer.repair import RepairResult
    # Patch repair_output to return something still invalid after repair
    invalid_repair = RepairResult(markdown="still invalid", actions=["some repair"], is_repaired=True)
    with patch("intelligent_regression_optimizer.llm_flow.repair_output", return_value=invalid_repair):
        client = FakeLLMClient(response_content=_make_unrepairable_output())
        result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), client)
    assert result.recommendation_mode == "deterministic-fallback"
    assert result.flow_result.exit_code == EXIT_OK


def test_fallback_path_output_passes_contract():
    from unittest.mock import patch
    from intelligent_regression_optimizer.repair import RepairResult
    invalid_repair = RepairResult(markdown="still invalid", actions=["some repair"], is_repaired=True)
    with patch("intelligent_regression_optimizer.llm_flow.repair_output", return_value=invalid_repair):
        client = FakeLLMClient(response_content=_make_unrepairable_output())
        result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), client)
    assert validate_output(result.flow_result.message).is_valid


# ---------------------------------------------------------------------------
# Generation error path
# ---------------------------------------------------------------------------

class ErrorClient:
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        raise RuntimeError("Connection timeout")


def test_generation_error_returns_exit_3():
    result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), ErrorClient())
    assert result.flow_result.exit_code == EXIT_GENERATION_ERROR


def test_generation_error_message_contains_detail():
    result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), ErrorClient())
    assert "Connection timeout" in result.flow_result.message


def test_generation_error_raw_output_is_none():
    result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), ErrorClient())
    assert result.raw_llm_output is None


# ---------------------------------------------------------------------------
# Recommendation Mode label in output matches recommendation_mode field
# ---------------------------------------------------------------------------

def test_recommendation_mode_label_matches_field_on_happy_path():
    client = FakeLLMClient()
    result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), client)
    assert f"Recommendation Mode: {result.recommendation_mode}" in result.flow_result.message


def test_recommendation_mode_label_matches_field_on_fallback():
    from unittest.mock import patch
    from intelligent_regression_optimizer.repair import RepairResult
    invalid_repair = RepairResult(markdown="still invalid", actions=["repair"], is_repaired=True)
    with patch("intelligent_regression_optimizer.llm_flow.repair_output", return_value=invalid_repair):
        client = FakeLLMClient(response_content="not valid")
        result = run_llm_pipeline(_base_normalized(), _make_classifications(), _make_tier_result(), client)
    assert "Recommendation Mode: deterministic-fallback" in result.flow_result.message
