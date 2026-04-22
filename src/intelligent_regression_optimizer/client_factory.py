"""Client factory — dispatches to the correct provider client."""
from __future__ import annotations

from intelligent_regression_optimizer.llm_client import LLMClient
from intelligent_regression_optimizer.models import ProviderConfig


def create_llm_client(config: ProviderConfig) -> LLMClient:
    """Return the appropriate LLMClient for config.provider."""
    if config.provider == "openai":
        from intelligent_regression_optimizer.openai_client import OpenAIClient
        return OpenAIClient(config)
    if config.provider == "ollama":
        from intelligent_regression_optimizer.ollama_client import OllamaClient
        return OllamaClient(config)
    if config.provider == "gemini":
        from intelligent_regression_optimizer.gemini_client import GeminiClient
        return GeminiClient(config)
    raise ValueError(
        f"Unknown LLM provider: {config.provider!r}. "
        "Supported providers: openai, ollama, gemini."
    )
