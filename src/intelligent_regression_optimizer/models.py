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
