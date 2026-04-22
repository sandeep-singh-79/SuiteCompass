"""Tests for structural repair of LLM-generated markdown."""
from __future__ import annotations

from intelligent_regression_optimizer.models import ScoredTest, TierResult
from intelligent_regression_optimizer.repair import repair_output


def _make_tier_result() -> TierResult:
    return TierResult(
        must_run=[ScoredTest("T-01", "Login", 9.0, "must-run", False, None, False)],
        budget_overflow=False,
    )


def _base_classifications() -> dict:
    return {
        "sprint_risk_level": "medium",
        "nfr_elevation_required": False,
    }


def _valid_markdown() -> str:
    return (
        "## Optimisation Summary\n\n"
        "Recommendation Mode: llm\n"
        "Sprint Risk Level: medium\n"
        "Total Must-Run: 1\n"
        "Total Retire Candidates: 0\n"
        "NFR Elevation: No\n"
        "Budget Overflow: No\n\n"
        "## Must-Run\n\n"
        "- T-01 Login (score: 9.0)\n\n"
        "## Should-Run If Time Permits\n\n"
        "_No tests in this tier._\n\n"
        "## Defer To Overnight Run\n\n"
        "_No tests in this tier._\n\n"
        "## Retire Candidates\n\n"
        "_No retire candidates._\n\n"
        "## Suite Health Summary\n\n"
        "Flakiness Tier High: 0 tests above threshold\n"
    )


# ---------------------------------------------------------------------------
# No-op when already valid
# ---------------------------------------------------------------------------

def test_no_repair_needed_when_valid():
    result = repair_output(_valid_markdown(), _make_tier_result(), _base_classifications())
    assert result.is_repaired is False
    assert result.actions == []
    assert result.markdown == _valid_markdown()


# ---------------------------------------------------------------------------
# Missing heading repair
# ---------------------------------------------------------------------------

def test_missing_heading_is_injected():
    md = _valid_markdown().replace("## Suite Health Summary\n", "")
    result = repair_output(md, _make_tier_result(), _base_classifications())
    assert result.is_repaired is True
    assert "## Suite Health Summary" in result.markdown
    assert any("Suite Health Summary" in a for a in result.actions)


# ---------------------------------------------------------------------------
# Missing label repair
# ---------------------------------------------------------------------------

def test_missing_label_is_injected():
    md = _valid_markdown().replace("Total Must-Run: 1\n", "")
    result = repair_output(md, _make_tier_result(), _base_classifications())
    assert result.is_repaired is True
    assert "Total Must-Run:" in result.markdown
    assert any("Total Must-Run" in a for a in result.actions)


# ---------------------------------------------------------------------------
# Duplicate label repair
# ---------------------------------------------------------------------------

def test_duplicate_label_is_deduplicated():
    md = _valid_markdown().replace(
        "Total Must-Run: 1\n",
        "Total Must-Run: 1\nTotal Must-Run: 1\n",
    )
    result = repair_output(md, _make_tier_result(), _base_classifications())
    assert result.is_repaired is True
    assert result.markdown.count("Total Must-Run:") == 1
    assert any("Duplicate" in a or "duplicate" in a for a in result.actions)


# ---------------------------------------------------------------------------
# Recommendation Mode fixup after repair
# ---------------------------------------------------------------------------

def test_recommendation_mode_set_to_llm_repaired_after_repair():
    md = _valid_markdown().replace("Total Must-Run: 1\n", "")
    result = repair_output(md, _make_tier_result(), _base_classifications())
    assert "Recommendation Mode: llm-repaired" in result.markdown


def test_recommendation_mode_unchanged_when_no_repair():
    result = repair_output(_valid_markdown(), _make_tier_result(), _base_classifications())
    assert "Recommendation Mode: llm" in result.markdown
    assert "llm-repaired" not in result.markdown


# ---------------------------------------------------------------------------
# Final output is contract-valid after repair
# ---------------------------------------------------------------------------

def test_repaired_output_passes_output_contract():
    from intelligent_regression_optimizer.output_validator import validate_output
    md = _valid_markdown().replace("Total Must-Run: 1\n", "").replace("## Suite Health Summary\n", "")
    result = repair_output(md, _make_tier_result(), _base_classifications())
    validation = validate_output(result.markdown)
    assert validation.is_valid, f"Repaired output failed: {validation.errors}"


def test_misplaced_label_is_moved_to_correct_section():
    # Flakiness Tier High belongs in Suite Health Summary but appears in Optimisation Summary
    md = _valid_markdown().replace(
        "## Suite Health Summary\n\nFlakiness Tier High: 0 tests above threshold\n",
        "## Suite Health Summary\n\n",
    ).replace(
        "Budget Overflow: No\n",
        "Budget Overflow: No\nFlakiness Tier High: 0 tests above threshold\n",
    )
    result = repair_output(md, _make_tier_result(), _base_classifications())
    assert result.is_repaired is True
    assert any("Moved" in a or "misplaced" in a.lower() for a in result.actions)
    from intelligent_regression_optimizer.output_validator import validate_output
    assert validate_output(result.markdown).is_valid


def test_all_label_values_are_repaired_correctly():
    """Repair an output missing all labels — exercises all _label_value branches."""
    from intelligent_regression_optimizer.output_validator import validate_output
    # Strip all label lines
    lines_to_strip = [
        "Recommendation Mode: llm",
        "Sprint Risk Level: medium",
        "Total Must-Run: 1",
        "Total Retire Candidates: 0",
        "NFR Elevation: No",
        "Budget Overflow: No",
        "Flakiness Tier High: 0 tests above threshold",
    ]
    md = _valid_markdown()
    for line in lines_to_strip:
        md = md.replace(line + "\n", "")
    tier = TierResult(
        must_run=[ScoredTest("T-01", "Login", 9.0, "must-run", False, None, False)],
        retire=[ScoredTest("T-99", "Old", 1.0, "retire", False, None, False)],
        budget_overflow=True,
    )
    classifications = {"sprint_risk_level": "high", "nfr_elevation_required": True}
    result = repair_output(md, tier, classifications)
    assert result.is_repaired is True
    assert "Total Must-Run: 1" in result.markdown
    assert "Total Retire Candidates: 1" in result.markdown
    assert "NFR Elevation: Yes" in result.markdown
    assert "Budget Overflow: Yes" in result.markdown
    assert "Sprint Risk Level: high" in result.markdown
    assert validate_output(result.markdown).is_valid
