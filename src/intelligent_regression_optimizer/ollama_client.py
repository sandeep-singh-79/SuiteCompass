"""Ollama LLM provider client."""
from __future__ import annotations

import json

from intelligent_regression_optimizer.llm_client import _post_json
from intelligent_regression_optimizer.models import (
    GenerationRequest,
    GenerationResponse,
    ProviderConfig,
)

_DEFAULT_BASE_URL = "http://localhost:11434"


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
        data = _post_json(
            url,
            payload,
            {"Content-Type": "application/json"},
            "Ollama",
        )

        return GenerationResponse(
            content=data["response"],
            model=data.get("model", self._config.model),
            provider="ollama",
        )
