"""Tests for V1-C CLI flags: --mode, --provider, --model, --base-url, --config, etc."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from intelligent_regression_optimizer.cli import main
from intelligent_regression_optimizer.models import EXIT_INPUT_ERROR, EXIT_OK


# ---------------------------------------------------------------------------
# Fixture: minimal valid input YAML
# ---------------------------------------------------------------------------

_MINIMAL_INPUT = {
    "sprint_context": {
        "sprint_name": "S1",
        "stories": [{"id": "US-1", "risk": "medium", "changed_areas": ["api"]}],
    },
    "test_suite": [
        {
            "id": "T-01",
            "name": "Login test",
            "layer": "e2e",
            "coverage_areas": ["api"],
            "execution_time_secs": 60,
            "flakiness_rate": 0.0,
            "automated": True,
        }
    ],
    "constraints": {"time_budget_mins": 60},
}


@pytest.fixture()
def input_file(tmp_path):
    p = tmp_path / "input.yaml"
    p.write_text(yaml.dump(_MINIMAL_INPUT), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Default mode: deterministic (no flags) — existing behaviour preserved
# ---------------------------------------------------------------------------

def test_default_mode_is_deterministic(input_file):
    runner = CliRunner()
    result = runner.invoke(main, ["run", input_file])
    assert result.exit_code == EXIT_OK
    assert "Recommendation Mode: deterministic" in result.output


# ---------------------------------------------------------------------------
# --mode deterministic explicit
# ---------------------------------------------------------------------------

def test_mode_deterministic_explicit(input_file):
    runner = CliRunner()
    result = runner.invoke(main, ["run", input_file, "--mode", "deterministic"])
    assert result.exit_code == EXIT_OK
    assert "Recommendation Mode: deterministic" in result.output


# ---------------------------------------------------------------------------
# --mode llm
# ---------------------------------------------------------------------------

def test_mode_llm_calls_llm_pipeline(input_file):
    from intelligent_regression_optimizer.llm_flow import LLMFlowResult
    from intelligent_regression_optimizer.models import FlowResult
    fake_result = LLMFlowResult(
        flow_result=FlowResult(exit_code=EXIT_OK, message="LLM report", output_path=None),
        recommendation_mode="llm",
        raw_llm_output="raw",
        repair_actions=[],
    )
    with patch("intelligent_regression_optimizer.cli.run_llm_pipeline", return_value=fake_result):
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", input_file,
            "--mode", "llm",
            "--provider", "openai",
            "--model", "gpt-4o",
        ], env={"IRO_LLM_API_KEY": "test-key"}, catch_exceptions=False)
    assert result.exit_code == EXIT_OK
    assert "LLM report" in result.output


def test_mode_llm_without_api_key_exits_with_error(input_file):
    runner = CliRunner()
    env = {k: v for k, v in os.environ.items() if k != "IRO_LLM_API_KEY"}
    env.pop("IRO_LLM_API_KEY", None)
    result = runner.invoke(main, [
        "run", input_file, "--mode", "llm", "--provider", "openai",
    ], env=env)
    assert result.exit_code == EXIT_INPUT_ERROR


# ---------------------------------------------------------------------------
# --mode compare
# ---------------------------------------------------------------------------

def test_mode_compare_calls_comparison(input_file):
    from intelligent_regression_optimizer.llm_flow import LLMFlowResult
    from intelligent_regression_optimizer.models import FlowResult
    fake_llm = LLMFlowResult(
        flow_result=FlowResult(exit_code=EXIT_OK, message="LLM report", output_path=None),
        recommendation_mode="llm",
        raw_llm_output="raw",
        repair_actions=[],
    )
    with patch("intelligent_regression_optimizer.cli.run_llm_pipeline", return_value=fake_llm):
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", input_file,
            "--mode", "compare",
            "--provider", "openai",
        ], env={"IRO_LLM_API_KEY": "test-key"}, catch_exceptions=False)
    assert result.exit_code == EXIT_OK
    assert "Comparison Summary" in result.output


# ---------------------------------------------------------------------------
# --config file is loaded
# ---------------------------------------------------------------------------

def test_config_file_is_loaded(input_file, tmp_path):
    config_file = tmp_path / "llm.yaml"
    config_file.write_text(yaml.dump({"provider": "ollama", "model": "llama3"}), encoding="utf-8")

    from intelligent_regression_optimizer.llm_flow import LLMFlowResult
    from intelligent_regression_optimizer.models import FlowResult
    fake_result = LLMFlowResult(
        flow_result=FlowResult(exit_code=EXIT_OK, message="Ollama report", output_path=None),
        recommendation_mode="llm",
        raw_llm_output="raw",
        repair_actions=[],
    )

    captured_config = {}
    original_run = None

    def capture_pipeline(normalized, classifications, tier_result, client):
        captured_config["client"] = client.__class__.__name__
        return fake_result

    with patch("intelligent_regression_optimizer.cli.run_llm_pipeline", side_effect=capture_pipeline):
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", input_file,
            "--mode", "llm",
            "--config", str(config_file),
        ], catch_exceptions=False)

    assert captured_config.get("client") == "OllamaClient"


# ---------------------------------------------------------------------------
# --mode invalid value is rejected
# ---------------------------------------------------------------------------

def test_invalid_mode_value_is_rejected(input_file):
    runner = CliRunner()
    result = runner.invoke(main, ["run", input_file, "--mode", "magic"])
    assert result.exit_code != EXIT_OK


# ---------------------------------------------------------------------------
# --mode llm with --output writes to file
# ---------------------------------------------------------------------------

def test_llm_mode_output_to_file(input_file, tmp_path):
    from intelligent_regression_optimizer.llm_flow import LLMFlowResult
    from intelligent_regression_optimizer.models import FlowResult
    fake_result = LLMFlowResult(
        flow_result=FlowResult(exit_code=EXIT_OK, message="LLM report to file", output_path=None),
        recommendation_mode="llm",
        raw_llm_output="raw",
        repair_actions=[],
    )
    out_file = tmp_path / "out.md"
    with patch("intelligent_regression_optimizer.cli.run_llm_pipeline", return_value=fake_result):
        runner = CliRunner()
        runner.invoke(main, [
            "run", input_file,
            "--mode", "llm",
            "--provider", "openai",
            "--output", str(out_file),
        ], env={"IRO_LLM_API_KEY": "test-key"}, catch_exceptions=False)
    assert out_file.exists()
    assert "LLM report to file" in out_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Provider exception — CLI must exit 0 with deterministic fallback report
# ---------------------------------------------------------------------------

def test_provider_exception_in_llm_mode_exits_ok_with_fallback(input_file):
    """Even if the LLM provider raises, the CLI must exit 0 with a deterministic fallback."""
    from intelligent_regression_optimizer.llm_flow import LLMFlowResult
    from intelligent_regression_optimizer.models import FlowResult
    # Simulate the new fallback-on-exception behavior from run_llm_pipeline
    fake_fallback = LLMFlowResult(
        flow_result=FlowResult(exit_code=EXIT_OK, message="Fallback report", output_path=None),
        recommendation_mode="deterministic-fallback",
        raw_llm_output=None,
        repair_actions=["Provider error: Network unreachable"],
    )
    with patch("intelligent_regression_optimizer.cli.run_llm_pipeline", return_value=fake_fallback):
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", input_file, "--mode", "llm", "--provider", "ollama",
        ], catch_exceptions=False)
    assert result.exit_code == EXIT_OK
    assert "Fallback report" in result.output
