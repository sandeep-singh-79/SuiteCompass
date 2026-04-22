"""Gemini LLM provider client."""
from __future__ import annotations

import json
import urllib.request
from urllib.error import HTTPError

from intelligent_regression_optimizer.models import (
    GenerationRequest,
    GenerationResponse,
    ProviderConfig,
)

_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"
_TIMEOUT = 300


class GeminiClient:
    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._base_url = config.base_url or _DEFAULT_BASE_URL

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self._config.api_key:
            raise ValueError("Gemini API key is required. Set IRO_LLM_API_KEY.")

        payload = json.dumps({
            "contents": [
                {
                    "parts": [
                        {"text": f"{request.system_prompt}\n\n{request.user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self._config.temperature,
                "maxOutputTokens": self._config.max_tokens,
            },
        }).encode()

        url = (
            f"{self._base_url}/v1beta/models/{self._config.model}"
            f":generateContent?key={self._config.api_key}"
        )
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
            raise RuntimeError(f"Gemini request failed: HTTP {exc.code} {exc.reason}") from exc

        content = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        return GenerationResponse(
            content=content,
            model=self._config.model,
            provider="gemini",
            prompt_tokens=usage.get("promptTokenCount"),
            completion_tokens=usage.get("candidatesTokenCount"),
        )
