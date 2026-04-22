"""Unit tests for renderer.py — written RED before implementation."""
import pytest
from intelligent_regression_optimizer.models import ScoredTest, TierResult
from intelligent_regression_optimizer.output_validator import (
    validate_output,
    REQUIRED_HEADINGS,
    REQUIRED_LABELS,
    LABEL_SECTION_MAP,
    parse_sections,
)
from intelligent_regression_optimizer.renderer import render_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scored(id_, name="test", score=5.0, tier="should-run", override=False,
            override_reason=None, is_manual=False, flakiness_rate=0.0):
    return ScoredTest(
        test_id=id_, name=name, raw_score=score, tier=tier,
        is_override=override, override_reason=override_reason, is_manual=is_manual,
        flakiness_rate=flakiness_rate,
    )


def _tier_result(must_run=None, should_run=None, defer=None, retire=None, overflow=False):
    return TierResult(
        must_run=must_run or [],
        should_run=should_run or [],
        defer=defer or [],
        retire=retire or [],
        budget_overflow=overflow,
    )


def _base_normalized(sprint_risk="high", budget_mins=30, flakiness_high=0.20):
    return {
        "sprint_context": {
            "sprint_id": "SPRINT-1",
            "stories": [{"id": "S1", "risk": sprint_risk, "changed_areas": ["ServiceA"], "resolved_deps": []}],
            "exploratory_sessions": [],
        },
        "test_suite": [
            {"id": "T1", "name": "payment e2e", "layer": "e2e",
             "coverage_areas": ["ServiceA"], "execution_time_secs": 120,
             "flakiness_rate": 0.01, "failure_count_last_30d": 0,
             "automated": True, "tags": []},
        ],
        "constraints": {
            "time_budget_mins": budget_mins,
            "mandatory_tags": [],
            "flakiness_retire_threshold": 0.30,
            "flakiness_high_tier_threshold": flakiness_high,
        },
    }


def _base_classifications(sprint_risk="high", nfr_elevation=True):
    return {
        "sprint_risk_level": sprint_risk,
        "nfr_elevation_required": nfr_elevation,
        "suite_health": "stable",
        "time_pressure": "relaxed",
        "per_test_stability": {"T1": 0.99},
    }


# ---------------------------------------------------------------------------
# Required headings
# ---------------------------------------------------------------------------

class TestRequiredHeadings:
    def test_all_required_headings_present(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result(must_run=[_scored("T1", score=10.0, tier="must-run")])
        output = render_report(normalized, classifications, tier)
        for heading in REQUIRED_HEADINGS:
            assert any(line.rstrip() == heading for line in output.splitlines()), \
                f"Missing heading: {heading!r}"

    def test_headings_are_line_anchored(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result()
        output = render_report(normalized, classifications, tier)
        for line in output.splitlines():
            stripped = line.rstrip()
            # If it's a required heading it must be at column 0 (not indented, not in prose)
            for heading in REQUIRED_HEADINGS:
                if heading in line and stripped != heading:
                    pytest.fail(f"Heading {heading!r} found embedded in prose: {line!r}")


# ---------------------------------------------------------------------------
# Required labels
# ---------------------------------------------------------------------------

class TestRequiredLabels:
    def test_all_required_labels_present(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result()
        output = render_report(normalized, classifications, tier)
        for label in REQUIRED_LABELS:
            assert label in output, f"Missing label: {label!r}"

    def test_labels_in_correct_sections(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result()
        output = render_report(normalized, classifications, tier)
        sections = parse_sections(output)
        for label, required_section in LABEL_SECTION_MAP.items():
            section_body = sections.get(required_section, "")
            assert label in section_body, \
                f"Label {label!r} not found in section {required_section!r}"

    def test_output_passes_validator(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result(must_run=[_scored("T1", score=10.0, tier="must-run")])
        output = render_report(normalized, classifications, tier)
        result = validate_output(output)
        assert result.is_valid, result.errors


# ---------------------------------------------------------------------------
# Budget overflow label
# ---------------------------------------------------------------------------

class TestBudgetOverflowLabel:
    def test_budget_overflow_label_yes_when_overflow(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result(overflow=True)
        output = render_report(normalized, classifications, tier)
        assert "Budget Overflow: yes" in output.lower() or "Budget Overflow: Yes" in output

    def test_budget_overflow_label_no_when_no_overflow(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result(overflow=False)
        output = render_report(normalized, classifications, tier)
        assert "Budget Overflow: no" in output.lower() or "Budget Overflow: No" in output


# ---------------------------------------------------------------------------
# Manual test tagging
# ---------------------------------------------------------------------------

class TestManualTestLabelling:
    def test_manual_tests_tagged_manual_in_output(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result(
            should_run=[_scored("T1", name="manual exploratory", is_manual=True, tier="should-run")]
        )
        output = render_report(normalized, classifications, tier)
        assert "(manual)" in output

    def test_automated_tests_not_tagged_manual(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result(
            must_run=[_scored("T1", name="automated e2e", is_manual=False, tier="must-run")]
        )
        output = render_report(normalized, classifications, tier)
        # "T1" appears but not tagged (manual)
        lines_with_t1 = [l for l in output.splitlines() if "T1" in l]
        for line in lines_with_t1:
            assert "(manual)" not in line


# ---------------------------------------------------------------------------
# Tier section content
# ---------------------------------------------------------------------------

class TestTierSectionContent:
    def test_must_run_section_lists_correct_tests(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result(
            must_run=[_scored("T1", name="critical test", score=10.0, tier="must-run")],
            should_run=[_scored("T2", name="secondary test", score=5.0, tier="should-run")],
        )
        output = render_report(normalized, classifications, tier)
        sections = parse_sections(output)
        must_body = sections.get("## Must-Run", "")
        should_body = sections.get("## Should-Run If Time Permits", "")
        assert "T1" in must_body
        assert "T2" not in must_body
        assert "T2" in should_body

    def test_retire_section_lists_retire_candidates(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result(
            retire=[_scored("T99", name="legacy smoke", score=-4.0, tier="retire")]
        )
        output = render_report(normalized, classifications, tier)
        sections = parse_sections(output)
        retire_body = sections.get("## Retire Candidates", "")
        assert "T99" in retire_body


# ---------------------------------------------------------------------------
# Suite health summary
# ---------------------------------------------------------------------------

class TestSuiteHealthSummary:
    def test_suite_health_summary_shows_total_tests(self):
        normalized = _base_normalized()
        classifications = _base_classifications()
        tier = _tier_result()
        output = render_report(normalized, classifications, tier)
        sections = parse_sections(output)
        health_body = sections.get("## Suite Health Summary", "")
        # Should mention something about flakiness tier high count
        assert "Flakiness Tier High:" in health_body

    def test_nfr_elevation_label_reflects_classification(self):
        # NFR elevation = True → "NFR Elevation: yes"
        normalized = _base_normalized()
        classifications = _base_classifications(nfr_elevation=True)
        tier = _tier_result()
        output = render_report(normalized, classifications, tier)
        assert "NFR Elevation: yes" in output.lower() or "NFR Elevation: Yes" in output


# ---------------------------------------------------------------------------
# Retire-candidate flakiness correctness (Critical fix #4)
# ---------------------------------------------------------------------------

class TestRetireCandidateFlakiness:
    def test_retire_candidate_shows_actual_flakiness_not_raw_score(self):
        """The (flakiness: X.XX) in retire output must be the test's
        flakiness_rate, not the computed raw_score."""
        normalized = _base_normalized()
        classifications = _base_classifications()
        # raw_score=6.15 but flakiness_rate=0.45
        retire_test = _scored(
            "T99", name="flaky api smoke", score=6.15, tier="retire",
            flakiness_rate=0.45,
        )
        tier = _tier_result(retire=[retire_test])
        output = render_report(normalized, classifications, tier)
        # Must contain actual flakiness
        assert "(flakiness: 0.45" in output
        # Must NOT contain the raw_score masquerading as flakiness
        assert "(flakiness: 6.15" not in output
