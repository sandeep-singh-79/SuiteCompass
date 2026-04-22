"""LLM config loader — 4-layer resolution: defaults → file → env → CLI."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from intelligent_regression_optimizer.models import ProviderConfig

_FORBIDDEN_FILE_KEYS: frozenset[str] = frozenset({"api_key"})

_DEFAULTS: dict[str, Any] = {
    "provider": "openai",
    "model": "gpt-4o",
    "base_url": None,
    "temperature": 0.3,
    "max_tokens": 4096,
}

_ENV_MAP = {
    "IRO_LLM_PROVIDER": "provider",
    "IRO_LLM_MODEL": "model",
    "IRO_LLM_BASE_URL": "base_url",
    "IRO_LLM_API_KEY": "api_key",
    "IRO_LLM_TEMPERATURE": "temperature",
    "IRO_LLM_MAX_TOKENS": "max_tokens",
}


def load_llm_config(
    config_path: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> ProviderConfig:
    """Resolve LLM config from 4 layers: defaults → config file → env vars → CLI flags.

    API key may only come from the IRO_LLM_API_KEY env var. Config files must
    not contain api_key.
    """
    config: dict[str, Any] = dict(_DEFAULTS)
    config["api_key"] = None

    # Layer 2: config file
    if config_path is not None:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"LLM config file not found: {config_path}")
        file_data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for key in _FORBIDDEN_FILE_KEYS:
            if key in file_data:
                raise ValueError(
                    f"LLM config file must not contain {key!r}. "
                    "Use the IRO_LLM_API_KEY environment variable instead."
                )
        for k, v in file_data.items():
            config[k] = v

    # Layer 3: env vars
    for env_key, config_key in _ENV_MAP.items():
        val = os.environ.get(env_key)
        if val is not None:
            if config_key == "temperature":
                config[config_key] = float(val)
            elif config_key == "max_tokens":
                config[config_key] = int(val)
            else:
                config[config_key] = val

    # Layer 4: CLI overrides (None values are ignored — no override)
    if cli_overrides:
        for config_key, val in cli_overrides.items():
            if val is not None:
                config[config_key] = val

    return ProviderConfig(
        provider=config["provider"],
        model=config["model"],
        base_url=config.get("base_url"),
        api_key=config.get("api_key"),
        temperature=float(config["temperature"]),
        max_tokens=int(config["max_tokens"]),
    )
