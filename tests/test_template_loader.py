"""Tests for template loader."""
from __future__ import annotations

import pytest
from pathlib import Path

from intelligent_regression_optimizer.template_loader import load_template


# ---------------------------------------------------------------------------
# Basic loading
# ---------------------------------------------------------------------------

def test_load_system_template_returns_string():
    content = load_template("system")
    assert isinstance(content, str)
    assert len(content) > 0


def test_load_high_risk_template():
    content = load_template("high_risk")
    assert isinstance(content, str)
    assert len(content) > 0


def test_load_degraded_suite_template():
    content = load_template("degraded_suite")
    assert isinstance(content, str)
    assert len(content) > 0


def test_load_budget_pressure_template():
    content = load_template("budget_pressure")
    assert isinstance(content, str)
    assert len(content) > 0


def test_load_balanced_template():
    content = load_template("balanced")
    assert isinstance(content, str)
    assert len(content) > 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_missing_template_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_template("nonexistent_template_xyz")


# ---------------------------------------------------------------------------
# Content checks
# ---------------------------------------------------------------------------

def test_system_template_contains_required_headings():
    content = load_template("system")
    for heading in [
        "## Optimisation Summary",
        "## Must-Run",
        "## Should-Run If Time Permits",
        "## Defer To Overnight Run",
        "## Retire Candidates",
        "## Suite Health Summary",
    ]:
        assert heading in content, f"system.txt missing heading: {heading!r}"


def test_system_template_contains_required_labels():
    content = load_template("system")
    for label in [
        "Recommendation Mode:",
        "Sprint Risk Level:",
        "Total Must-Run:",
        "Total Retire Candidates:",
        "NFR Elevation:",
        "Budget Overflow:",
        "Flakiness Tier High:",
    ]:
        assert label in content, f"system.txt missing label: {label!r}"


def test_scenario_templates_contain_placeholders():
    for name in ("high_risk", "degraded_suite", "budget_pressure", "balanced"):
        content = load_template(name)
        assert "{" in content and "}" in content, (
            f"{name}.txt has no {{placeholders}}"
        )


# ---------------------------------------------------------------------------
# Custom prompt_dir override
# ---------------------------------------------------------------------------

def test_custom_prompt_dir(tmp_path):
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir(parents=True)
    (v1_dir / "custom.txt").write_text("Hello {name}", encoding="utf-8")

    content = load_template("custom", prompt_dir=tmp_path)
    assert content == "Hello {name}"


def test_custom_prompt_dir_missing_template_raises(tmp_path):
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        load_template("missing", prompt_dir=tmp_path)
