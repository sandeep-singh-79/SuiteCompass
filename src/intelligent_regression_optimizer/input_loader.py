"""Input loader and validator for intelligent-regression-optimizer."""
from __future__ import annotations

import pathlib
from typing import Any

import yaml

from intelligent_regression_optimizer.models import InputPackage

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

VALID_RISK_VALUES = {"high", "medium", "low"}


class InputValidationError(ValueError):
    """Raised when the input YAML fails structural or semantic validation."""


# ---------------------------------------------------------------------------
# Internal validators
# ---------------------------------------------------------------------------

def _require_keys(obj: dict, keys: list[str], context: str) -> None:
    for key in keys:
        if key not in obj:
            raise InputValidationError(f"Missing required field {key!r} in {context}")


def _validate_story(story: dict, index: int) -> None:
    ctx = f"story[{index}]"
    _require_keys(story, ["id", "risk", "changed_areas"], ctx)
    if story["risk"] not in VALID_RISK_VALUES:
        raise InputValidationError(
            f"Invalid risk value {story['risk']!r} in {ctx}. "
            f"Must be one of {sorted(VALID_RISK_VALUES)}"
        )
    dep_stories = story.get("dependency_stories", [])
    if not isinstance(dep_stories, list):
        raise InputValidationError(
            f"dependency_stories must be a list in {ctx}, got {type(dep_stories).__name__}"
        )


def _validate_test(test: dict, index: int) -> None:
    ctx = f"test_suite[{index}]"
    _require_keys(test, ["id", "name", "layer", "coverage_areas", "execution_time_secs", "flakiness_rate"], ctx)

    exec_time = test["execution_time_secs"]
    if not isinstance(exec_time, (int, float)) or exec_time < 0:
        raise InputValidationError(
            f"execution_time_secs must be a non-negative number in {ctx}, got {exec_time!r}"
        )

    flakiness = test["flakiness_rate"]
    if not isinstance(flakiness, (int, float)) or not (0.0 <= flakiness <= 1.0):
        raise InputValidationError(
            f"flakiness_rate must be between 0.0 and 1.0 in {ctx}, got {flakiness!r}"
        )


def _resolve_deps(stories: list[dict]) -> list[dict]:
    """Add a ``resolved_deps`` list to each story (1-hop only)."""
    story_map: dict[str, dict] = {s["id"]: s for s in stories}
    result = []
    for story in stories:
        dep_ids: list[str] = story.get("dependency_stories", [])
        resolved = []
        for dep_id in dep_ids:
            if dep_id not in story_map:
                raise InputValidationError(
                    f"Dependency story {dep_id!r} referenced by {story['id']!r} "
                    f"not found in sprint_context.stories"
                )
            resolved.append(story_map[dep_id])
        result.append({**story, "resolved_deps": resolved})
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate a raw input dict and return normalised data.

    This is the shared validation logic used by both :func:`load_input`
    (file-based) and the merge utility (dict-based).

    Args:
        raw: Top-level dict with sprint_context, test_suite, constraints.

    Returns:
        Normalised dict ready for the pipeline.

    Raises:
        :class:`InputValidationError` for structural or semantic errors.
    """
    if not isinstance(raw, dict):
        raise InputValidationError("Input YAML must be a mapping at the top level")

    # Required top-level keys
    _require_keys(raw, ["sprint_context", "test_suite", "constraints"], "root")

    sprint = raw["sprint_context"]
    _require_keys(sprint, ["stories"], "sprint_context")

    # Validate stories is a list
    stories = sprint.get("stories", [])
    if not isinstance(stories, list):
        raise InputValidationError(
            f"sprint_context.stories must be a list, got {type(stories).__name__}"
        )
    for i, story in enumerate(stories):
        _validate_story(story, i)

    # Validate test_suite is a list
    test_suite = raw.get("test_suite", [])
    if not isinstance(test_suite, list):
        raise InputValidationError(
            f"test_suite must be a list, got {type(test_suite).__name__}"
        )
    for i, test in enumerate(test_suite):
        _validate_test(test, i)

    # Validate mandatory_tags is a list if present
    constraints = raw.get("constraints", {})
    mandatory_tags = constraints.get("mandatory_tags", [])
    if not isinstance(mandatory_tags, list):
        raise InputValidationError(
            f"constraints.mandatory_tags must be a list, got {type(mandatory_tags).__name__}"
        )

    # Resolve 1-hop dependencies
    resolved_stories = _resolve_deps(stories)

    # Build normalised document
    normalized: dict[str, Any] = {
        **raw,
        "sprint_context": {
            **sprint,
            "stories": resolved_stories,
            "exploratory_sessions": sprint.get("exploratory_sessions", []),
        },
    }

    return normalized


def load_input(path: str) -> InputPackage:
    """Load, parse, and validate an input YAML file.

    Args:
        path: Absolute or relative path to the input YAML.

    Returns:
        :class:`InputPackage` with ``raw`` and ``normalized`` data.

    Raises:
        :class:`InputValidationError` for structural or semantic errors.
        :class:`FileNotFoundError` if the file does not exist.
    """
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {path!r}")

    with p.open(encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh)

    normalized = validate_raw(raw)

    return InputPackage(source_path=path, raw=raw, normalized=normalized)
