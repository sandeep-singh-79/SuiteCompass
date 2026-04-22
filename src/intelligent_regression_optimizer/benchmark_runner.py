"""Benchmark assertion runner for intelligent-regression-optimizer.

Checks a rendered markdown report against a YAML assertions file.
"""
from __future__ import annotations

import pathlib
from typing import Any

import yaml

from intelligent_regression_optimizer.models import ValidationResult


def run_assertions(markdown: str, assertions_path: str) -> ValidationResult:
    """Run all assertions in *assertions_path* against *markdown*.

    Supported assertion keys:
    - ``must_include_headings``: list of strings that must appear as line-anchored headings
    - ``must_include_labels``: list of label strings that must appear anywhere
    - ``must_include_substrings``: list of substrings that must appear anywhere
    - ``must_not_include_substrings``: list of substrings that must NOT appear

    Args:
        markdown:         The rendered report to validate.
        assertions_path:  Path to a YAML assertions file.

    Returns:
        :class:`ValidationResult` with errors for each failing assertion.
    """
    p = pathlib.Path(assertions_path)
    with p.open(encoding="utf-8") as fh:
        assertions: dict[str, Any] = yaml.safe_load(fh) or {}

    errors: list[str] = []
    total = 0

    # --- must_include_headings (line-anchored) ------------------------------
    lines = markdown.splitlines()
    present_headings = {line.rstrip() for line in lines}

    for heading in assertions.get("must_include_headings", []):
        total += 1
        if heading not in present_headings:
            errors.append(f"Missing required heading: {heading!r}")

    # --- must_include_labels ------------------------------------------------
    for label in assertions.get("must_include_labels", []):
        total += 1
        if label not in markdown:
            errors.append(f"Missing required label: {label!r}")

    # --- must_include_substrings --------------------------------------------
    for substring in assertions.get("must_include_substrings", []):
        total += 1
        if substring not in markdown:
            errors.append(f"Missing required substring: {substring!r}")

    # --- must_not_include_substrings ----------------------------------------
    for substring in assertions.get("must_not_include_substrings", []):
        total += 1
        if substring in markdown:
            errors.append(f"Forbidden substring found: {substring!r}")

    # --- min_section_word_count ---------------------------------------------
    # Extract per-section text (up to the next ## heading or end of document)
    import re
    section_map: dict[str, str] = {}
    for m in re.finditer(r"(## [^\n]+)\n(.*?)(?=\n## |\Z)", markdown, re.DOTALL):
        section_map[m.group(1).rstrip()] = m.group(2)

    for heading, min_words in assertions.get("min_section_word_count", {}).items():
        total += 1
        if heading not in section_map:
            errors.append(f"Section not found for word-count check: {heading!r}")
            continue
        word_count = len(section_map[heading].split())
        if word_count < min_words:
            errors.append(
                f"Section {heading!r} has {word_count} words, need >= {min_words}"
            )

    return ValidationResult(errors=errors, total_checks=total)
