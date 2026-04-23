"""LLM client Protocol and FakeLLMClient for testing."""
from __future__ import annotations

import json
import urllib.request
from typing import Protocol, runtime_checkable
from urllib.error import HTTPError

from intelligent_regression_optimizer.models import (
    GenerationRequest,
    GenerationResponse,
)

# ---------------------------------------------------------------------------
# A minimal but fully contract-compliant report used by FakeLLMClient.
# All 7 headings and all 8 labels present, Recommendation Mode set to "llm".
# ---------------------------------------------------------------------------
_FAKE_RESPONSE = """\
## Optimisation Summary

Recommendation Mode: llm
Sprint Risk Level: medium
Total Must-Run: 1
Total Flaky Critical: 0
Total Retire Candidates: 0
NFR Elevation: No
Budget Overflow: No

This sprint targets medium-risk changes. The LLM analysis confirms that focused
regression coverage is sufficient, with one test elevated to must-run based on
its direct coverage of the modified area and its historically strong signal.

## Must-Run

T-01 covers the core integration path that was directly changed in this sprint.
This test must execute before any sign-off because a regression here would
affect every downstream consumer. Its coverage of the primary data flow makes
it the single highest-priority item in the current run budget.

- T-01 Sample test (score: 9.0)

## Flaky Critical Coverage

_No flaky-critical tests._

## Should-Run If Time Permits

_No tests in this tier._

## Defer To Overnight Run

_No tests in this tier._

## Retire Candidates

_No retire candidates._

## Suite Health Summary

Flakiness Tier High: 0 tests above threshold
Total automated execution time (must-run): 2 min
Time budget: 60 min
Suite stability is strong. No flaky tests were detected above the high-tier
threshold. No remediation actions are required for the current sprint cycle.

## Warnings

_No warnings._
"""


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for all LLM provider clients."""

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        ...


class FakeLLMClient:
    """Deterministic client for testing. Returns a pre-computed valid report."""

    def __init__(self, response_content: str | None = None) -> None:
        self._content = response_content if response_content is not None else _FAKE_RESPONSE

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        return GenerationResponse(
            content=self._content,
            model="fake",
            provider="fake",
        )


# ---------------------------------------------------------------------------
# Shared HTTP helper for provider clients (package-internal)
# ---------------------------------------------------------------------------

_TIMEOUT: int = 300


def _post_json(
    url: str, payload: bytes, headers: dict[str, str], provider_name: str
) -> dict:
    """POST payload to url and return parsed JSON response.

    Raises RuntimeError with the HTTP status on non-2xx responses.
    Internal utility shared by provider clients; not part of the public API.
    """
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        raise RuntimeError(
            f"{provider_name} request failed: HTTP {exc.code} {exc.reason}"
        ) from exc
