"""Git diff → coverage area mapper for intelligent-regression-optimizer.

Loads an area-map.yaml config that declares fnmatch glob patterns → coverage areas,
then maps a list of changed files (from `git diff --name-only`) to the set of
coverage areas they touch.

Public API:
  load_area_map(path)             -> list[AreaMapping]
  parse_diff_output(text)         -> list[str]
  map_files_to_areas(files, maps) -> set[str]
"""
from __future__ import annotations

import fnmatch
import pathlib
from dataclasses import dataclass, field

import yaml

from intelligent_regression_optimizer.input_loader import InputValidationError


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AreaMapping:
    """A single glob-pattern → coverage-area mapping entry."""

    pattern: str
    areas: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_area_map(path: str) -> list[AreaMapping]:
    """Load and validate an area-map.yaml config file.

    Expected format::

        mappings:
          - pattern: "src/payments/**"
            areas: [PaymentService]
          - pattern: "tests/**"
            areas: []

    Args:
        path: Absolute or relative path to the YAML config.

    Returns:
        Ordered list of :class:`AreaMapping` entries.

    Raises:
        :class:`InputValidationError` on missing file, parse error, or
        schema violations.
    """
    p = pathlib.Path(path)
    if not p.exists():
        raise InputValidationError(f"Area map file not found: {path!r}")

    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise InputValidationError(f"Failed to parse area map {path!r}: {exc}") from exc

    if not isinstance(raw, dict):
        raise InputValidationError(
            f"Area map {path!r} must be a YAML mapping at the top level"
        )

    if "mappings" not in raw:
        raise InputValidationError(
            f"Area map {path!r} is missing required key 'mappings'"
        )

    mappings_raw = raw["mappings"]
    if not isinstance(mappings_raw, list):
        raise InputValidationError(
            f"'mappings' in {path!r} must be a list, got {type(mappings_raw).__name__}"
        )

    result: list[AreaMapping] = []
    for i, entry in enumerate(mappings_raw):
        ctx = f"mappings[{i}] in {path!r}"

        if not isinstance(entry, dict):
            raise InputValidationError(f"{ctx} must be a mapping, got {type(entry).__name__}")

        if "pattern" not in entry:
            raise InputValidationError(f"{ctx} is missing required key 'pattern'")

        if "areas" not in entry:
            raise InputValidationError(f"{ctx} is missing required key 'areas'")

        pattern = entry["pattern"]
        if not isinstance(pattern, str):
            raise InputValidationError(
                f"'pattern' in {ctx} must be a string, got {type(pattern).__name__}"
            )

        areas = entry["areas"]
        if not isinstance(areas, list):
            raise InputValidationError(
                f"'areas' in {ctx} must be a list, got {type(areas).__name__}"
            )

        result.append(AreaMapping(pattern=pattern, areas=list(areas)))

    return result


def parse_diff_output(text: str) -> list[str]:
    """Extract changed file paths from `git diff --name-only` output.

    Blank lines and whitespace-only lines are ignored.  Both Unix (``\\n``)
    and Windows (``\\r\\n``) line endings are handled.

    Args:
        text: Raw text output of ``git diff --name-only``.

    Returns:
        List of file path strings in the order they appeared.
    """
    return [line.strip() for line in text.splitlines() if line.strip()]


def map_files_to_areas(
    files: list[str],
    mappings: list[AreaMapping],
) -> set[str]:
    """Map a list of changed files to coverage areas using fnmatch patterns.

    Each file is matched against every mapping pattern.  All areas from all
    matching patterns are union-merged into the result set.  Files that match
    no pattern and patterns with empty ``areas`` both contribute nothing.

    Matching uses :func:`fnmatch.fnmatch`, which supports ``*``, ``**``
    (treated as ``*`` by fnmatch on a flat string — callers should use
    single ``*`` for single-directory globs and ``**`` for recursive matching
    with the understanding that fnmatch treats ``**`` as matching any sequence
    of characters including path separators).

    Args:
        files: List of changed file paths (relative to repository root).
        mappings: Ordered list of :class:`AreaMapping` entries.

    Returns:
        Set of coverage area strings.
    """
    result: set[str] = set()
    for file_path in files:
        for mapping in mappings:
            if fnmatch.fnmatch(file_path, mapping.pattern):
                result.update(mapping.areas)
    return result


def apply_area_map(normalized: dict, areas: set[str]) -> dict:
    """Return a new normalized dict with every story's changed_areas replaced.

    The derived *areas* set overwrites ``changed_areas`` on every story.
    The original dict is not mutated.
    """
    areas_list = sorted(areas)
    updated_stories = [
        {**story, "changed_areas": areas_list}
        for story in normalized.get("sprint_context", {}).get("stories", [])
    ]
    return {
        **normalized,
        "sprint_context": {
            **normalized.get("sprint_context", {}),
            "stories": updated_stories,
        },
    }
