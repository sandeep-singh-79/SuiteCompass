"""Tests for OpenAI, Ollama, and Gemini provider clients."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from intelligent_regression_optimizer.models import (
    GenerationRequest,
    GenerationResponse,
    ProviderConfig,
)
from intelligent_regression_optimizer.llm_client import LLMClient


def _make_config(provider: str, api_key: str | None = "test-key", base_url: str | None = None) -> ProviderConfig:
    return ProviderConfig(
        provider=provider,
        model="test-model",
        base_url=base_url,
        api_key=api_key,
        temperature=0.3,
        max_tokens=512,
    )


def _make_request() -> GenerationRequest:
    return GenerationRequest(
        system_prompt="You are a test assistant.",
        user_prompt="Produce a report.",
    )


# ---------------------------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------------------------

class TestOpenAIClient:
    def test_satisfies_protocol(self):
        from intelligent_regression_optimizer.openai_client import OpenAIClient
        client = OpenAIClient(_make_config("openai"))
        assert isinstance(client, LLMClient)

    def test_generate_returns_response(self):
        from intelligent_regression_optimizer.openai_client import OpenAIClient
        cfg = _make_config("openai")
        req = _make_request()
        mock_resp = {
            "choices": [{"message": {"content": "Hello"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        with patch("urllib.request.urlopen") as mock_open:
            mock_cm = MagicMock()
            mock_cm.__enter__ = MagicMock(return_value=mock_cm)
            mock_cm.__exit__ = MagicMock(return_value=False)
            mock_cm.read.return_value = json.dumps(mock_resp).encode()
            mock_open.return_value = mock_cm
            resp = OpenAIClient(cfg).generate(req)
        assert isinstance(resp, GenerationResponse)
        assert resp.content == "Hello"
        assert resp.provider == "openai"
        assert resp.prompt_tokens == 10
        assert resp.completion_tokens == 5

    def test_missing_api_key_raises(self):
        from intelligent_regression_optimizer.openai_client import OpenAIClient
        cfg = _make_config("openai", api_key=None)
        with pytest.raises(ValueError, match="API key"):
            OpenAIClient(cfg).generate(_make_request())

    def test_uses_bearer_auth_header(self):
        from intelligent_regression_optimizer.openai_client import OpenAIClient
        cfg = _make_config("openai", api_key="sk-secret")
        req = _make_request()
        mock_resp = {
            "choices": [{"message": {"content": "ok"}}],
            "model": "test-model",
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        captured = {}
        with patch("urllib.request.urlopen") as mock_open:
            mock_cm = MagicMock()
            mock_cm.__enter__ = MagicMock(return_value=mock_cm)
            mock_cm.__exit__ = MagicMock(return_value=False)
            mock_cm.read.return_value = json.dumps(mock_resp).encode()
            mock_open.return_value = mock_cm

            def capture_request(req_obj, timeout=None):
                captured["headers"] = dict(req_obj.headers)
                return mock_cm

            mock_open.side_effect = capture_request
            OpenAIClient(cfg).generate(req)
        assert "Authorization" in captured["headers"]
        assert captured["headers"]["Authorization"] == "Bearer sk-secret"

    def test_http_error_raises(self):
        from urllib.error import HTTPError
        from intelligent_regression_optimizer.openai_client import OpenAIClient
        cfg = _make_config("openai")
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            url="http://x", code=500, msg="Server Error", hdrs=None, fp=None
        )):
            with pytest.raises(RuntimeError, match="500"):
                OpenAIClient(cfg).generate(_make_request())

    def test_default_base_url(self):
        from intelligent_regression_optimizer.openai_client import OpenAIClient
        cfg = _make_config("openai", api_key="key")
        client = OpenAIClient(cfg)
        assert "openai" in client._base_url


# ---------------------------------------------------------------------------
# Ollama client
# ---------------------------------------------------------------------------

class TestOllamaClient:
    def test_satisfies_protocol(self):
        from intelligent_regression_optimizer.ollama_client import OllamaClient
        client = OllamaClient(_make_config("ollama", api_key=None, base_url="http://localhost:11434"))
        assert isinstance(client, LLMClient)

    def test_generate_returns_response(self):
        from intelligent_regression_optimizer.ollama_client import OllamaClient
        cfg = _make_config("ollama", api_key=None, base_url="http://localhost:11434")
        req = _make_request()
        mock_resp = {"response": "Hello from ollama", "model": "test-model"}
        with patch("urllib.request.urlopen") as mock_open:
            mock_cm = MagicMock()
            mock_cm.__enter__ = MagicMock(return_value=mock_cm)
            mock_cm.__exit__ = MagicMock(return_value=False)
            mock_cm.read.return_value = json.dumps(mock_resp).encode()
            mock_open.return_value = mock_cm
            resp = OllamaClient(cfg).generate(req)
        assert isinstance(resp, GenerationResponse)
        assert resp.content == "Hello from ollama"
        assert resp.provider == "ollama"
        assert resp.prompt_tokens is None

    def test_no_auth_header(self):
        from intelligent_regression_optimizer.ollama_client import OllamaClient
        cfg = _make_config("ollama", api_key=None, base_url="http://localhost:11434")
        req = _make_request()
        mock_resp = {"response": "ok", "model": "test-model"}
        captured = {}
        with patch("urllib.request.urlopen") as mock_open:
            mock_cm = MagicMock()
            mock_cm.__enter__ = MagicMock(return_value=mock_cm)
            mock_cm.__exit__ = MagicMock(return_value=False)
            mock_cm.read.return_value = json.dumps(mock_resp).encode()

            def capture(req_obj, timeout=None):
                captured["headers"] = dict(req_obj.headers)
                return mock_cm

            mock_open.side_effect = capture
            OllamaClient(cfg).generate(req)
        assert "Authorization" not in captured["headers"]

    def test_http_error_raises(self):
        from urllib.error import HTTPError
        from intelligent_regression_optimizer.ollama_client import OllamaClient
        cfg = _make_config("ollama", api_key=None, base_url="http://localhost:11434")
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            url="http://x", code=503, msg="Unavailable", hdrs=None, fp=None
        )):
            with pytest.raises(RuntimeError, match="503"):
                OllamaClient(cfg).generate(_make_request())

    def test_default_base_url(self):
        from intelligent_regression_optimizer.ollama_client import OllamaClient
        cfg = _make_config("ollama", api_key=None)
        client = OllamaClient(cfg)
        assert "11434" in client._base_url


# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------

class TestGeminiClient:
    def test_satisfies_protocol(self):
        from intelligent_regression_optimizer.gemini_client import GeminiClient
        client = GeminiClient(_make_config("gemini", api_key="gemini-key"))
        assert isinstance(client, LLMClient)

    def test_generate_returns_response(self):
        from intelligent_regression_optimizer.gemini_client import GeminiClient
        cfg = _make_config("gemini", api_key="gemini-key")
        req = _make_request()
        mock_resp = {
            "candidates": [{"content": {"parts": [{"text": "Hello from Gemini"}]}}],
            "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 4},
        }
        with patch("urllib.request.urlopen") as mock_open:
            mock_cm = MagicMock()
            mock_cm.__enter__ = MagicMock(return_value=mock_cm)
            mock_cm.__exit__ = MagicMock(return_value=False)
            mock_cm.read.return_value = json.dumps(mock_resp).encode()
            mock_open.return_value = mock_cm
            resp = GeminiClient(cfg).generate(req)
        assert isinstance(resp, GenerationResponse)
        assert resp.content == "Hello from Gemini"
        assert resp.provider == "gemini"
        assert resp.prompt_tokens == 8
        assert resp.completion_tokens == 4

    def test_missing_api_key_raises(self):
        from intelligent_regression_optimizer.gemini_client import GeminiClient
        cfg = _make_config("gemini", api_key=None)
        with pytest.raises(ValueError, match="API key"):
            GeminiClient(cfg).generate(_make_request())

    def test_api_key_in_url_not_header(self):
        from intelligent_regression_optimizer.gemini_client import GeminiClient
        cfg = _make_config("gemini", api_key="my-gemini-key")
        req = _make_request()
        mock_resp = {
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
            "usageMetadata": {},
        }
        captured = {}
        with patch("urllib.request.urlopen") as mock_open:
            mock_cm = MagicMock()
            mock_cm.__enter__ = MagicMock(return_value=mock_cm)
            mock_cm.__exit__ = MagicMock(return_value=False)
            mock_cm.read.return_value = json.dumps(mock_resp).encode()

            def capture(req_obj, timeout=None):
                captured["url"] = req_obj.full_url
                captured["headers"] = dict(req_obj.headers)
                return mock_cm

            mock_open.side_effect = capture
            GeminiClient(cfg).generate(req)
        assert "my-gemini-key" in captured["url"]
        assert "Authorization" not in captured["headers"]

    def test_http_error_raises(self):
        from urllib.error import HTTPError
        from intelligent_regression_optimizer.gemini_client import GeminiClient
        cfg = _make_config("gemini", api_key="key")
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            url="http://x", code=401, msg="Unauthorized", hdrs=None, fp=None
        )):
            with pytest.raises(RuntimeError, match="401"):
                GeminiClient(cfg).generate(_make_request())
