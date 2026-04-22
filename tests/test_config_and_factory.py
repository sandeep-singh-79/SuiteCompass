"""Tests for LLM config loader and client factory."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from intelligent_regression_optimizer.models import ProviderConfig
from intelligent_regression_optimizer.config_loader import load_llm_config
from intelligent_regression_optimizer.client_factory import create_llm_client
from intelligent_regression_optimizer.llm_client import LLMClient


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

def test_defaults_when_no_config_no_env_no_cli():
    with patch.dict(os.environ, {}, clear=False):
        for key in ("IRO_LLM_PROVIDER", "IRO_LLM_MODEL", "IRO_LLM_BASE_URL",
                    "IRO_LLM_API_KEY", "IRO_LLM_TEMPERATURE", "IRO_LLM_MAX_TOKENS"):
            os.environ.pop(key, None)
        cfg = load_llm_config()
    assert cfg.provider == "openai"
    assert cfg.model == "gpt-4o"
    assert cfg.temperature == 0.3
    assert cfg.max_tokens == 4096
    assert cfg.api_key is None
    assert cfg.base_url is None


# ---------------------------------------------------------------------------
# Config file layer
# ---------------------------------------------------------------------------

def test_config_file_sets_provider_and_model(tmp_path):
    config_file = tmp_path / "llm.yaml"
    config_file.write_text(yaml.dump({"provider": "ollama", "model": "llama3"}), encoding="utf-8")
    with patch.dict(os.environ, {}, clear=False):
        for key in ("IRO_LLM_PROVIDER", "IRO_LLM_MODEL"):
            os.environ.pop(key, None)
        cfg = load_llm_config(config_path=str(config_file))
    assert cfg.provider == "ollama"
    assert cfg.model == "llama3"


def test_config_file_with_api_key_raises(tmp_path):
    config_file = tmp_path / "llm.yaml"
    config_file.write_text(yaml.dump({"provider": "openai", "api_key": "secret"}), encoding="utf-8")
    with pytest.raises(ValueError, match="api_key"):
        load_llm_config(config_path=str(config_file))


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_llm_config(config_path=str(tmp_path / "nonexistent.yaml"))


# ---------------------------------------------------------------------------
# Env var layer
# ---------------------------------------------------------------------------

def test_env_var_overrides_config_file(tmp_path):
    config_file = tmp_path / "llm.yaml"
    config_file.write_text(yaml.dump({"provider": "ollama", "model": "llama3"}), encoding="utf-8")
    with patch.dict(os.environ, {"IRO_LLM_PROVIDER": "gemini"}, clear=False):
        os.environ.pop("IRO_LLM_MODEL", None)
        cfg = load_llm_config(config_path=str(config_file))
    assert cfg.provider == "gemini"


def test_env_var_api_key_is_loaded():
    with patch.dict(os.environ, {"IRO_LLM_API_KEY": "env-key"}, clear=False):
        cfg = load_llm_config()
    assert cfg.api_key == "env-key"


def test_env_var_temperature_parsed_as_float():
    with patch.dict(os.environ, {"IRO_LLM_TEMPERATURE": "0.7"}, clear=False):
        cfg = load_llm_config()
    assert cfg.temperature == pytest.approx(0.7)


def test_env_var_max_tokens_parsed_as_int():
    with patch.dict(os.environ, {"IRO_LLM_MAX_TOKENS": "2048"}, clear=False):
        cfg = load_llm_config()
    assert cfg.max_tokens == 2048


# ---------------------------------------------------------------------------
# CLI override layer
# ---------------------------------------------------------------------------

def test_cli_overrides_env_var():
    with patch.dict(os.environ, {"IRO_LLM_PROVIDER": "ollama"}, clear=False):
        cfg = load_llm_config(cli_overrides={"provider": "gemini"})
    assert cfg.provider == "gemini"


def test_cli_overrides_model():
    cfg = load_llm_config(cli_overrides={"model": "gpt-4-turbo"})
    assert cfg.model == "gpt-4-turbo"


def test_cli_none_values_do_not_override(tmp_path):
    config_file = tmp_path / "llm.yaml"
    config_file.write_text(yaml.dump({"model": "llama3"}), encoding="utf-8")
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("IRO_LLM_MODEL", None)
        cfg = load_llm_config(config_path=str(config_file), cli_overrides={"model": None})
    assert cfg.model == "llama3"


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def test_factory_creates_openai_client():
    from intelligent_regression_optimizer.openai_client import OpenAIClient
    cfg = ProviderConfig(provider="openai", model="gpt-4o", base_url=None,
                        api_key=None, temperature=0.3, max_tokens=4096)
    client = create_llm_client(cfg)
    assert isinstance(client, OpenAIClient)


def test_factory_creates_ollama_client():
    from intelligent_regression_optimizer.ollama_client import OllamaClient
    cfg = ProviderConfig(provider="ollama", model="llama3", base_url=None,
                        api_key=None, temperature=0.3, max_tokens=4096)
    client = create_llm_client(cfg)
    assert isinstance(client, OllamaClient)


def test_factory_creates_gemini_client():
    from intelligent_regression_optimizer.gemini_client import GeminiClient
    cfg = ProviderConfig(provider="gemini", model="gemini-pro", base_url=None,
                        api_key=None, temperature=0.3, max_tokens=4096)
    client = create_llm_client(cfg)
    assert isinstance(client, GeminiClient)


def test_factory_returns_llm_client_protocol():
    cfg = ProviderConfig(provider="openai", model="gpt-4o", base_url=None,
                        api_key=None, temperature=0.3, max_tokens=4096)
    client = create_llm_client(cfg)
    assert isinstance(client, LLMClient)


def test_factory_unknown_provider_raises():
    cfg = ProviderConfig(provider="unknown_xyz", model="x", base_url=None,
                        api_key=None, temperature=0.3, max_tokens=4096)
    with pytest.raises(ValueError, match="unknown_xyz"):
        create_llm_client(cfg)
