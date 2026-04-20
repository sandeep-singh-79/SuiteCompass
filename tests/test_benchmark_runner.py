"""Direct unit tests for benchmark_runner.run_assertions()."""

from __future__ import annotations

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
