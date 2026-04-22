"""Data models for intelligent-regression-optimizer."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------

EXIT_OK: int = 0
EXIT_VALIDATION_ERROR: int = 1
EXIT_INPUT_ERROR: int = 2

# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------


@dataclass
class InputPackage:
    """Parsed and normalised input document."""

    source_path: str
    raw: dict[str, Any]
    normalized: dict[str, Any]


@dataclass
class ScoredTest:
    """A single test together with its computed scoring result."""

    test_id: str
    name: str
    raw_score: float
    tier: str                     # "must-run" | "should-run" | "defer" | "retire"
    is_override: bool
    override_reason: str | None
    is_manual: bool
    flakiness_rate: float = 0.0


@dataclass
class TierResult:
    """Full tiering result for a sprint run."""

    must_run: list[ScoredTest] = field(default_factory=list)
    should_run: list[ScoredTest] = field(default_factory=list)
    defer: list[ScoredTest] = field(default_factory=list)
    retire: list[ScoredTest] = field(default_factory=list)
    budget_overflow: bool = False


@dataclass
class ValidationResult:
    """Output of a structural validation pass."""

    errors: list[str]
    total_checks: int

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


@dataclass
class FlowResult:
    """Final result returned by the end-to-end pipeline."""

    exit_code: int
    message: str
    output_path: str | None
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# V1-A: Test history data structures
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class TestHistoryRecord:
    """Per-test metrics derived from CI history or a pre-computed summary file."""

    test_id: str
    flakiness_rate: float
    failure_count_last_30d: int
    total_runs: int
    last_run_date: str | None = None


# ---------------------------------------------------------------------------
# V1-C: LLM integration data structures
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ProviderConfig:
    """Configuration for an LLM provider."""

    provider: str
    model: str
    base_url: str | None
    api_key: str | None
    temperature: float
    max_tokens: int


@dataclass(slots=True)
class GenerationRequest:
    """Input to an LLM generate call."""

    system_prompt: str
    user_prompt: str


@dataclass(slots=True)
class GenerationResponse:
    """Output from an LLM generate call."""

    content: str
    model: str
    provider: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
