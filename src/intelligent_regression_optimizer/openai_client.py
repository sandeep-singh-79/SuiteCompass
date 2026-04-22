"""OpenAI LLM provider client."""
from __future__ import annotations

import json
import urllib.request
from urllib.error import HTTPError

from intelligent_regression_optimizer.models import (
    GenerationRequest,
    GenerationResponse,
    ProviderConfig,
)

_DEFAULT_BASE_URL = "https://api.openai.com"
_TIMEOUT = 300


class OpenAIClient:
    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._base_url = config.base_url or _DEFAULT_BASE_URL

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self._config.api_key:
            raise ValueError("OpenAI API key is required. Set IRO_LLM_API_KEY.")

        payload = json.dumps({
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
        }).encode()

        url = f"{self._base_url}/v1/chat/completions"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._config.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read())
        except HTTPError as exc:
            raise RuntimeError(f"OpenAI request failed: HTTP {exc.code} {exc.reason}") from exc

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return GenerationResponse(
            content=content,
            model=data.get("model", self._config.model),
            provider="openai",
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )
