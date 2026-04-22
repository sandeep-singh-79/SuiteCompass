"""Ollama LLM provider client."""
from __future__ import annotations

import json
import urllib.request
from urllib.error import HTTPError

from intelligent_regression_optimizer.models import (
    GenerationRequest,
    GenerationResponse,
    ProviderConfig,
)

_DEFAULT_BASE_URL = "http://localhost:11434"
_TIMEOUT = 300


class OllamaClient:
    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._base_url = config.base_url or _DEFAULT_BASE_URL

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        prompt = f"{request.system_prompt}\n\n{request.user_prompt}"
        payload = json.dumps({
            "model": self._config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self._config.temperature,
                "num_predict": self._config.max_tokens,
            },
        }).encode()

        url = f"{self._base_url}/api/generate"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read())
        except HTTPError as exc:
            raise RuntimeError(f"Ollama request failed: HTTP {exc.code} {exc.reason}") from exc

        return GenerationResponse(
            content=data["response"],
            model=data.get("model", self._config.model),
            provider="ollama",
        )
