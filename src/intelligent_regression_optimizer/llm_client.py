"""LLM client Protocol and FakeLLMClient for testing."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from intelligent_regression_optimizer.models import (
    GenerationRequest,
    GenerationResponse,
)

# ---------------------------------------------------------------------------
# A minimal but fully contract-compliant report used by FakeLLMClient.
# All 6 headings and all 7 labels present, Recommendation Mode set to "llm".
# ---------------------------------------------------------------------------
_FAKE_RESPONSE = """\
## Optimisation Summary

Recommendation Mode: llm
Sprint Risk Level: medium
Total Must-Run: 1
Total Retire Candidates: 0
NFR Elevation: No
Budget Overflow: No

## Must-Run

- T-01 Sample test (score: 9.0)

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
