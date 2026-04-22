"""Direct unit tests for benchmark_runner.run_assertions()."""

from __future__ import annotations

from pathlib import Path

import pytest

from intelligent_regression_optimizer.benchmark_runner import run_assertions


VALID_MARKDOWN = """\
## Optimisation Summary

Recommendation Mode: deterministic
Sprint Risk Level: high
Total Must-Run: 3
Total Retire Candidates: 0
NFR Elevation: Yes
Budget Overflow: No

## Must-Run

- T001 login test (score: 12.0)

## Should-Run If Time Permits

- T002 search test (score: 6.5)

## Defer To Overnight Run

_None._

## Retire Candidates

_No retire candidates._

## Suite Health Summary

Flakiness Tier High: 0 tests above threshold
"""


class TestRunAssertionsHeadings:
    def test_all_headings_present_passes(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text('must_include_headings:\n  - "## Optimisation Summary"\n  - "## Must-Run"\n')
        r = run_assertions(VALID_MARKDOWN, str(f))
        assert r.is_valid
        assert r.total_checks == 2

    def test_missing_heading_fails(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text('must_include_headings:\n  - "## NONEXISTENT SECTION"\n')
        r = run_assertions(VALID_MARKDOWN, str(f))
        assert not r.is_valid
        assert any("NONEXISTENT" in e for e in r.errors)

    def test_partial_heading_not_matched(self, repo_tmp):
        """Line-anchored: a partial substring must not match a full line."""
        f = repo_tmp / "a.yaml"
        f.write_text('must_include_headings:\n  - "## Optimisation"\n')
        r = run_assertions(VALID_MARKDOWN, str(f))
        assert not r.is_valid


class TestRunAssertionsLabels:
    def test_present_label_passes(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text('must_include_labels:\n  - "Sprint Risk Level:"\n')
        r = run_assertions(VALID_MARKDOWN, str(f))
        assert r.is_valid

    def test_missing_label_fails(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text('must_include_labels:\n  - "Missing Label:"\n')
        r = run_assertions(VALID_MARKDOWN, str(f))
        assert not r.is_valid
        assert any("Missing Label" in e for e in r.errors)


class TestRunAssertionsSubstrings:
    def test_present_substring_passes(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text('must_include_substrings:\n  - "T001 login test"\n')
        r = run_assertions(VALID_MARKDOWN, str(f))
        assert r.is_valid

    def test_missing_substring_fails(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text('must_include_substrings:\n  - "XYZZY_NEVER_FOUND"\n')
        r = run_assertions(VALID_MARKDOWN, str(f))
        assert not r.is_valid
        assert any("XYZZY_NEVER_FOUND" in e for e in r.errors)

    def test_absent_forbidden_substring_passes(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text('must_not_include_substrings:\n  - "XYZZY_NOT_HERE"\n')
        r = run_assertions(VALID_MARKDOWN, str(f))
        assert r.is_valid

    def test_present_forbidden_substring_fails(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text('must_not_include_substrings:\n  - "T001 login test"\n')
        r = run_assertions(VALID_MARKDOWN, str(f))
        assert not r.is_valid
        assert any("Forbidden substring found" in e for e in r.errors)


class TestRunAssertionsTotalChecks:
    def test_total_checks_counts_all_assertions(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text(
            "must_include_headings:\n  - '## Must-Run'\n"
            "must_include_labels:\n  - 'Sprint Risk Level:'\n"
            "must_include_substrings:\n  - 'T001'\n"
            "must_not_include_substrings:\n  - 'XYZZY'\n"
        )
        r = run_assertions(VALID_MARKDOWN, str(f))
        assert r.is_valid
        assert r.total_checks == 4

    def test_empty_assertions_file_returns_zero_checks(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text("{}\n")
        r = run_assertions(VALID_MARKDOWN, str(f))
        assert r.is_valid
        assert r.total_checks == 0


# ---------------------------------------------------------------------------
# R4: min_section_word_count — narrative quality assertions (F4)
# ---------------------------------------------------------------------------

_NARRATIVE_REPORT = """\
## Optimisation Summary

Recommendation Mode: llm
Sprint Risk Level: high
Total Must-Run: 1
Total Retire Candidates: 0
NFR Elevation: No
Budget Overflow: No

This sprint carries elevated risk. The payment API changes require thorough coverage.
All high-priority tests must execute before the release window closes.

## Must-Run

This sprint introduces significant changes to the payment processing flow.
T-01 must run because it covers the critical checkout path that was modified.
Skipping it would leave the core business transaction unverified before release.

- T-01 Checkout flow test (score: 9.5)

## Should-Run If Time Permits

_No tests in this tier._

## Defer To Overnight Run

_No tests in this tier._

## Retire Candidates

_No retire candidates._

## Suite Health Summary

Flakiness Tier High: 0 tests above threshold
The suite is stable and well-maintained. No immediate remediation is required.
"""

_STRUCTURAL_ONLY_REPORT = """\
## Optimisation Summary

Recommendation Mode: llm
Sprint Risk Level: high
Total Must-Run: 1
Total Retire Candidates: 0
NFR Elevation: No
Budget Overflow: No

## Must-Run

- T-01 Checkout flow test (score: 9.5)

## Should-Run If Time Permits

_No tests in this tier._

## Defer To Overnight Run

_No tests in this tier._

## Retire Candidates

_No retire candidates._

## Suite Health Summary

Flakiness Tier High: 0 tests above threshold
"""


class TestMinSectionWordCount:
    """min_section_word_count assertion type: minimum words within a named section."""

    def test_narrative_report_passes_word_count_check(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text(
            "min_section_word_count:\n"
            "  '## Must-Run': 15\n"
        )
        r = run_assertions(_NARRATIVE_REPORT, str(f))
        assert r.is_valid, r.errors

    def test_structural_only_report_fails_word_count_check(self, repo_tmp):
        """A report with labels and bullets but no narrative prose must fail."""
        f = repo_tmp / "a.yaml"
        f.write_text(
            "min_section_word_count:\n"
            "  '## Must-Run': 15\n"
        )
        r = run_assertions(_STRUCTURAL_ONLY_REPORT, str(f))
        assert not r.is_valid
        assert any("Must-Run" in e for e in r.errors)

    def test_word_count_counts_against_correct_section_only(self, repo_tmp):
        """Words from other sections must not inflate the count for the checked section."""
        f = repo_tmp / "a.yaml"
        f.write_text(
            "min_section_word_count:\n"
            "  '## Retire Candidates': 20\n"  # retire section has very few words
        )
        r = run_assertions(_NARRATIVE_REPORT, str(f))
        assert not r.is_valid

    def test_min_section_word_count_adds_to_total_checks(self, repo_tmp):
        f = repo_tmp / "a.yaml"
        f.write_text(
            "must_include_headings:\n  - '## Must-Run'\n"
            "min_section_word_count:\n  '## Must-Run': 15\n"
        )
        r = run_assertions(_NARRATIVE_REPORT, str(f))
        assert r.total_checks == 2

    def test_missing_section_fails_word_count(self, repo_tmp):
        """Asserting a word count for a section absent from the report must fail."""
        f = repo_tmp / "a.yaml"
        f.write_text(
            "min_section_word_count:\n"
            "  '## Nonexistent Section': 5\n"
        )
        r = run_assertions(_NARRATIVE_REPORT, str(f))
        assert not r.is_valid


# ---------------------------------------------------------------------------
# LLM benchmark integration — full pipeline with FakeLLMClient
# ---------------------------------------------------------------------------

_BENCHMARKS = Path(__file__).parent.parent / "benchmarks"


class TestLLMBenchmarkIntegration:
    """End-to-end: LLM pipeline with FakeLLMClient passes the LLM benchmark assertions.

    This is the regression anchor for V1-C. It verifies that:
    - run_llm_pipeline() completes without error using FakeLLMClient
    - The output satisfies all assertions in llm-enhanced-high-risk.assertions.yaml
    - The Recommendation Mode label is "llm" (not "deterministic")
    """

    def _run_llm_pipeline_on_high_risk(self):
        from intelligent_regression_optimizer.context_classifier import classify_context
        from intelligent_regression_optimizer.input_loader import load_input
        from intelligent_regression_optimizer.llm_client import FakeLLMClient
        from intelligent_regression_optimizer.llm_flow import run_llm_pipeline
        from intelligent_regression_optimizer.scoring_engine import score_tests

        pkg = load_input(str(_BENCHMARKS / "high-risk-feature-sprint.input.yaml"))
        classifications = classify_context(pkg.normalized)
        tier_result = score_tests(pkg.normalized, classifications)
        return run_llm_pipeline(pkg.normalized, classifications, tier_result, FakeLLMClient())

    def test_llm_pipeline_exits_0(self):
        from intelligent_regression_optimizer.models import EXIT_OK
        result = self._run_llm_pipeline_on_high_risk()
        assert result.flow_result.exit_code == EXIT_OK

    def test_llm_benchmark_assertions_pass(self):
        result = self._run_llm_pipeline_on_high_risk()
        ar = run_assertions(
            result.flow_result.message,
            str(_BENCHMARKS / "llm-enhanced-high-risk.assertions.yaml"),
        )
        assert ar.is_valid, f"LLM benchmark assertions failed: {ar.errors}"

    def test_llm_benchmark_total_checks_nonzero(self):
        result = self._run_llm_pipeline_on_high_risk()
        ar = run_assertions(
            result.flow_result.message,
            str(_BENCHMARKS / "llm-enhanced-high-risk.assertions.yaml"),
        )
        assert ar.total_checks > 0

    def test_recommendation_mode_is_llm(self):
        result = self._run_llm_pipeline_on_high_risk()
        assert "Recommendation Mode: llm" in result.flow_result.message

    def test_recommendation_mode_is_not_deterministic(self):
        result = self._run_llm_pipeline_on_high_risk()
        assert "Recommendation Mode: deterministic" not in result.flow_result.message

    def test_llm_benchmark_narrative_word_counts_pass(self):
        """Must-Run section must contain actual prose, not just bullet labels."""
        result = self._run_llm_pipeline_on_high_risk()
        ar = run_assertions(
            result.flow_result.message,
            str(_BENCHMARKS / "llm-enhanced-high-risk.assertions.yaml"),
        )
        # This test passes only if assertions.yaml includes min_section_word_count checks
        assert ar.total_checks > len([
            "must_include_headings", "must_include_labels",
            "must_include_substrings", "must_not_include_substrings",
        ]), "assertions.yaml must include min_section_word_count to prove narrative quality"
        assert ar.is_valid, f"Narrative quality assertions failed: {ar.errors}"
