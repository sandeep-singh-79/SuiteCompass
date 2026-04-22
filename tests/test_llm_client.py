"""Tests for LLM client Protocol and FakeLLMClient."""
from __future__ import annotations

import pytest

from intelligent_regression_optimizer.models import (
    EXIT_GENERATION_ERROR,
    GenerationRequest,
    GenerationResponse,
    ProviderConfig,
)
from intelligent_regression_optimizer.llm_client import FakeLLMClient, LLMClient
from intelligent_regression_optimizer.output_validator import validate_output


# ---------------------------------------------------------------------------
# Exit code
# ---------------------------------------------------------------------------

def test_exit_generation_error_value():
    assert EXIT_GENERATION_ERROR == 3


# ---------------------------------------------------------------------------
# ProviderConfig
# ---------------------------------------------------------------------------

def test_provider_config_fields():
    cfg = ProviderConfig(
        provider="openai",
        model="gpt-4o",
        base_url=None,
        api_key=None,
        temperature=0.3,
        max_tokens=4096,
    )
    assert cfg.provider == "openai"
    assert cfg.model == "gpt-4o"
    assert cfg.base_url is None
    assert cfg.api_key is None
    assert cfg.temperature == 0.3
    assert cfg.max_tokens == 4096


def test_provider_config_with_base_url():
    cfg = ProviderConfig(
        provider="ollama",
        model="llama3",
        base_url="http://localhost:11434",
        api_key=None,
        temperature=0.5,
        max_tokens=2048,
    )
    assert cfg.base_url == "http://localhost:11434"


# ---------------------------------------------------------------------------
# GenerationRequest
# ---------------------------------------------------------------------------

def test_generation_request_fields():
    req = GenerationRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Explain the test results.",
    )
    assert req.system_prompt == "You are a helpful assistant."
    assert req.user_prompt == "Explain the test results."


# ---------------------------------------------------------------------------
# GenerationResponse
# ---------------------------------------------------------------------------

def test_generation_response_fields():
    resp = GenerationResponse(
        content="## Optimisation Summary\n",
        model="gpt-4o",
        provider="openai",
    )
    assert resp.content == "## Optimisation Summary\n"
    assert resp.model == "gpt-4o"
    assert resp.provider == "openai"
    assert resp.prompt_tokens is None
    assert resp.completion_tokens is None


def test_generation_response_with_token_counts():
    resp = GenerationResponse(
        content="output",
        model="gpt-4o",
        provider="openai",
        prompt_tokens=100,
        completion_tokens=200,
    )
    assert resp.prompt_tokens == 100
    assert resp.completion_tokens == 200


# ---------------------------------------------------------------------------
# LLMClient Protocol
# ---------------------------------------------------------------------------

def test_fake_llm_client_satisfies_protocol():
    client = FakeLLMClient()
    assert isinstance(client, LLMClient)


def test_fake_llm_client_generate_returns_response():
    req = GenerationRequest(
        system_prompt="sys", user_prompt="usr",
    )
    client = FakeLLMClient()
    resp = client.generate(req)
    assert isinstance(resp, GenerationResponse)
    assert resp.provider == "fake"
    assert resp.model == "fake"


def test_fake_llm_client_default_response_passes_output_contract():
    req = GenerationRequest(system_prompt="sys", user_prompt="usr")
    client = FakeLLMClient()
    resp = client.generate(req)
    result = validate_output(resp.content)
    assert result.is_valid, f"FakeLLMClient default response failed validation: {result.errors}"


def test_fake_llm_client_custom_response():
    custom = "## Optimisation Summary\n\nRecommendation Mode: llm\nSprint Risk Level: high\nTotal Must-Run: 1\nTotal Retire Candidates: 0\nNFR Elevation: No\nBudget Overflow: No\n\n## Must-Run\n\n- T-01 Login test (score: 9.0)\n\n## Should-Run If Time Permits\n\n_No tests in this tier._\n\n## Defer To Overnight Run\n\n_No tests in this tier._\n\n## Retire Candidates\n\n_No retire candidates._\n\n## Suite Health Summary\n\nFlakiness Tier High: 0 tests above threshold\nTotal automated execution time (must-run): 5 min\nTime budget: 60 min\n"
    req = GenerationRequest(system_prompt="sys", user_prompt="usr")
    client = FakeLLMClient(response_content=custom)
    resp = client.generate(req)
    assert resp.content == custom


def test_fake_llm_client_default_response_contains_llm_mode():
    req = GenerationRequest(system_prompt="sys", user_prompt="usr")
    resp = FakeLLMClient().generate(req)
    assert "Recommendation Mode: llm" in resp.content
