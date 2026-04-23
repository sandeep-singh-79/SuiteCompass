"""Unit tests for output_validator.py — written RED before implementation."""
import pytest
from intelligent_regression_optimizer.output_validator import validate_output

# ---------------------------------------------------------------------------
# Minimal valid output — used as baseline for negative tests
# ---------------------------------------------------------------------------

VALID_OUTPUT = """\
## Optimisation Summary

Recommendation Mode: deterministic
Sprint Risk Level: high
Total Must-Run: 3
Total Flaky Critical: 1
Total Retire Candidates: 1
NFR Elevation: yes
Budget Overflow: no

## Must-Run

- TEST-001 payment flow e2e (score: 10.0)
- TEST-002 retry handler integration (score: 9.4) [override: mandatory]
- TEST-003 payment service security (score: 8.0) [override: nfr-elevation]

## Flaky Critical Coverage

- TEST-007 flaky auth test (flakiness: 0.35, unique: [auth], action: stabilize or replace)

## Should-Run If Time Permits

- TEST-004 order facade unit (score: 6.0)

## Defer To Overnight Run

- TEST-005 reporting dashboard e2e (score: 2.1)

## Retire Candidates

- TEST-006 legacy smoke (flakiness: 0.42, no unique coverage)

## Suite Health Summary

Flakiness Tier High: 3 tests above 0.20
Total automated execution time (must-run): 14 min
"""


class TestValidOutputPasses:
    def test_valid_output_passes(self):
        result = validate_output(VALID_OUTPUT)
        assert result.is_valid, result.errors


class TestMissingHeadings:
    @pytest.mark.parametrize("heading", [
        "## Optimisation Summary",
        "## Must-Run",
        "## Should-Run If Time Permits",
        "## Defer To Overnight Run",
        "## Retire Candidates",
        "## Suite Health Summary",
    ])
    def test_missing_heading_fails(self, heading):
        broken = "\n".join(
            line for line in VALID_OUTPUT.splitlines()
            if line.rstrip() != heading
        )
        result = validate_output(broken)
        assert not result.is_valid
        assert any(heading in e for e in result.errors)

    def test_heading_embedded_in_prose_fails(self):
        # Heading present only inside a sentence — must not satisfy line-anchor check
        output = VALID_OUTPUT.replace(
            "## Must-Run\n",
            "See the ## Must-Run section below\n",
        )
        result = validate_output(output)
        assert not result.is_valid

    def test_indented_heading_fails(self):
        output = VALID_OUTPUT.replace(
            "## Must-Run\n",
            "  ## Must-Run\n",
        )
        result = validate_output(output)
        assert not result.is_valid


class TestMissingLabels:
    @pytest.mark.parametrize("label", [
        "Recommendation Mode:",
        "Sprint Risk Level:",
        "Total Must-Run:",
        "Total Retire Candidates:",
        "NFR Elevation:",
        "Budget Overflow:",
        "Flakiness Tier High:",
    ])
    def test_missing_label_fails(self, label):
        broken = "\n".join(
            line for line in VALID_OUTPUT.splitlines()
            if not line.startswith(label)
        )
        result = validate_output(broken)
        assert not result.is_valid
        assert any(label in e for e in result.errors)


class TestDuplicateLabel:
    def test_duplicate_label_fails(self):
        output = VALID_OUTPUT.replace(
            "Sprint Risk Level: high",
            "Sprint Risk Level: high\nSprint Risk Level: medium",
        )
        result = validate_output(output)
        assert not result.is_valid
        assert any("duplicate" in e.lower() or "Sprint Risk Level:" in e for e in result.errors)


class TestLabelInWrongSection:
    def test_label_in_wrong_section_fails(self):
        # Move "Flakiness Tier High:" from Suite Health Summary into Optimisation Summary
        output = VALID_OUTPUT.replace(
            "Budget Overflow: no\n",
            "Budget Overflow: no\nFlakiness Tier High: misplaced\n",
        ).replace(
            "\nFlakiness Tier High: 3 tests above 0.20",
            "",
        )
        result = validate_output(output)
        assert not result.is_valid


class TestEmptyInput:
    def test_empty_string_fails(self):
        result = validate_output("")
        assert not result.is_valid

    def test_headings_only_no_labels_fails(self):
        output = "\n".join([
            "## Optimisation Summary",
            "## Must-Run",
            "## Should-Run If Time Permits",
            "## Defer To Overnight Run",
            "## Retire Candidates",
            "## Suite Health Summary",
        ])
        result = validate_output(output)
        assert not result.is_valid


class TestTotalChecksReported:
    def test_total_checks_nonzero(self):
        result = validate_output(VALID_OUTPUT)
        assert result.total_checks > 0


# ---------------------------------------------------------------------------
# F2.1 — Flaky Critical Coverage heading + Total Flaky Critical label
# ---------------------------------------------------------------------------

class TestFlakyCriticalOutputContract:
    def test_missing_flaky_critical_heading_fails(self):
        broken = "\n".join(
            line for line in VALID_OUTPUT.splitlines()
            if line.rstrip() != "## Flaky Critical Coverage"
        )
        result = validate_output(broken)
        assert not result.is_valid
        assert any("## Flaky Critical Coverage" in e for e in result.errors)

    def test_missing_total_flaky_critical_label_fails(self):
        broken = "\n".join(
            line for line in VALID_OUTPUT.splitlines()
            if not line.startswith("Total Flaky Critical:")
        )
        result = validate_output(broken)
        assert not result.is_valid
        assert any("Total Flaky Critical:" in e for e in result.errors)

    def test_total_flaky_critical_in_wrong_section_fails(self):
        # Move Total Flaky Critical label to Suite Health Summary
        broken = VALID_OUTPUT.replace(
            "Total Flaky Critical: 1\n",
            "",
        ).replace(
            "Flakiness Tier High:",
            "Total Flaky Critical: 1\nFlakiness Tier High:",
        )
        result = validate_output(broken)
        assert not result.is_valid
