"""Unit tests for junit_xml_parser.py — written RED before implementation (TDD A2)."""
from __future__ import annotations

import datetime
import pathlib
import xml.etree.ElementTree as ET

import pytest

from intelligent_regression_optimizer.input_loader import InputValidationError
from intelligent_regression_optimizer.junit_xml_parser import parse_junit_directory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_suite_xml(
    testcases: list[tuple[str, str | None, bool, bool]],
    timestamp: str | None = None,
) -> str:
    """Build a <testsuite> XML string.

    testcases: list of (name, classname_or_None, failed, skipped)
    """
    suite = ET.Element("testsuite")
    suite.set("name", "Tests")
    if timestamp:
        suite.set("timestamp", timestamp)
    for name, classname, failed, skipped in testcases:
        tc = ET.SubElement(suite, "testcase")
        tc.set("name", name)
        if classname:
            tc.set("classname", classname)
        if skipped:
            ET.SubElement(tc, "skipped")
        elif failed:
            f = ET.SubElement(tc, "failure")
            f.set("message", "AssertionError")
    return ET.tostring(suite, encoding="unicode")


def _write(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParseJunitDirectory:

    # --- directory-level ---

    def test_empty_directory_returns_empty_dict(self, tmp_path):
        result = parse_junit_directory(str(tmp_path))
        assert result == {}

    def test_directory_not_found_raises(self, tmp_path):
        p = tmp_path / "nonexistent"
        with pytest.raises(InputValidationError, match="not found"):
            parse_junit_directory(str(p))

    def test_non_xml_files_ignored(self, tmp_path):
        (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")
        _write(tmp_path / "run-01.xml", _make_suite_xml([("t", "X", False, False)]))
        result = parse_junit_directory(str(tmp_path))
        assert "X::t" in result
        assert len(result) == 1

    # --- single file ---

    def test_single_file_all_pass(self, tmp_path):
        xml = _make_suite_xml([
            ("test_login", "tests.Auth", False, False),
            ("test_logout", "tests.Auth", False, False),
        ])
        _write(tmp_path / "run-01.xml", xml)
        result = parse_junit_directory(str(tmp_path))
        assert "tests.Auth::test_login" in result
        rec = result["tests.Auth::test_login"]
        assert rec.flakiness_rate == pytest.approx(0.0)
        assert rec.failure_count_last_30d == 0
        assert rec.total_runs == 1

    def test_single_file_some_fail(self, tmp_path):
        # Single run: failure without adjacent pass → flakiness unknown → 0.0
        # failure_count_last_30d still records the failure
        xml = _make_suite_xml([
            ("test_a", "P.T", False, False),
            ("test_b", "P.T", True, False),
        ])
        _write(tmp_path / "run-01.xml", xml)
        result = parse_junit_directory(str(tmp_path))
        assert result["P.T::test_a"].flakiness_rate == pytest.approx(0.0)
        assert result["P.T::test_b"].flakiness_rate == pytest.approx(0.0)
        assert result["P.T::test_b"].failure_count_last_30d == 1

    # --- multiple files ---

    def test_multiple_files_all_pass_rate_is_zero(self, tmp_path):
        for i in range(3):
            _write(tmp_path / f"run-0{i}.xml", _make_suite_xml([("t", "X", False, False)]))
        result = parse_junit_directory(str(tmp_path))
        assert result["X::t"].flakiness_rate == pytest.approx(0.0)
        assert result["X::t"].total_runs == 3

    def test_multiple_files_consistent_failures_are_not_flaky(self, tmp_path):
        # 4 consecutive failures with no intervening pass → not flaky (consistently broken)
        for i in range(4):
            _write(tmp_path / f"run-0{i}.xml", _make_suite_xml([("t", "X", True, False)]))
        result = parse_junit_directory(str(tmp_path))
        assert result["X::t"].flakiness_rate == pytest.approx(0.0)
        assert result["X::t"].total_runs == 4

    def test_multiple_files_mixed_correct_flakiness_rate(self, tmp_path):
        # 3 runs: fail, pass, fail → 2/3
        _write(tmp_path / "run-01.xml", _make_suite_xml([("t", "X", True, False)]))
        _write(tmp_path / "run-02.xml", _make_suite_xml([("t", "X", False, False)]))
        _write(tmp_path / "run-03.xml", _make_suite_xml([("t", "X", True, False)]))
        result = parse_junit_directory(str(tmp_path))
        assert result["X::t"].flakiness_rate == pytest.approx(2 / 3)
        assert result["X::t"].total_runs == 3

    def test_test_in_subset_of_files_uses_subset_total(self, tmp_path):
        # test_a in 3 runs; test_b in only 2
        _write(tmp_path / "run-01.xml", _make_suite_xml([("ta", "X", False, False), ("tb", "X", True, False)]))
        _write(tmp_path / "run-02.xml", _make_suite_xml([("ta", "X", False, False), ("tb", "X", False, False)]))
        _write(tmp_path / "run-03.xml", _make_suite_xml([("ta", "X", True, False)]))
        result = parse_junit_directory(str(tmp_path))
        assert result["X::ta"].total_runs == 3
        assert result["X::tb"].total_runs == 2

    # --- test-case-level edge cases ---

    def test_skipped_tests_excluded_from_results(self, tmp_path):
        xml = _make_suite_xml([
            ("test_normal", "X", False, False),
            ("test_skip", "X", False, True),
        ])
        _write(tmp_path / "run-01.xml", xml)
        result = parse_junit_directory(str(tmp_path))
        assert "X::test_normal" in result
        assert "X::test_skip" not in result

    def test_error_element_counts_as_failure(self, tmp_path):
        # <error> is treated as failure; single run → flakiness_rate=0.0 (no adjacent run to compare)
        # failure_count_last_30d still records the failure
        suite = ET.Element("testsuite")
        suite.set("name", "T")
        tc = ET.SubElement(suite, "testcase")
        tc.set("name", "test_err")
        tc.set("classname", "Pkg")
        err = ET.SubElement(tc, "error")
        err.set("message", "RuntimeError")
        _write(tmp_path / "run-01.xml", ET.tostring(suite, encoding="unicode"))
        result = parse_junit_directory(str(tmp_path))
        assert result["Pkg::test_err"].flakiness_rate == pytest.approx(0.0)
        assert result["Pkg::test_err"].failure_count_last_30d == 1

    def test_classname_included_in_test_id(self, tmp_path):
        xml = _make_suite_xml([("test_x", "com.example.MyTest", False, False)])
        _write(tmp_path / "run-01.xml", xml)
        result = parse_junit_directory(str(tmp_path))
        assert "com.example.MyTest::test_x" in result

    def test_no_classname_uses_name_only(self, tmp_path):
        xml = _make_suite_xml([("standalone_test", None, False, False)])
        _write(tmp_path / "run-01.xml", xml)
        result = parse_junit_directory(str(tmp_path))
        assert "standalone_test" in result

    # --- XML format variants ---

    def test_surefire_testsuites_wrapper_supported(self, tmp_path):
        root = ET.Element("testsuites")
        suite = ET.SubElement(root, "testsuite")
        suite.set("name", "T")
        tc = ET.SubElement(suite, "testcase")
        tc.set("name", "test_y")
        tc.set("classname", "Pkg")
        _write(tmp_path / "surefire.xml", ET.tostring(root, encoding="unicode"))
        result = parse_junit_directory(str(tmp_path))
        assert "Pkg::test_y" in result

    # --- timestamp-based failure_count_last_30d ---

    def test_recent_timestamps_included_in_failure_count(self, tmp_path):
        ref = datetime.date(2026, 4, 21)
        recent_ts = "2026-04-10T10:00:00"   # 11 days before ref → within 30d
        old_ts = "2026-03-01T10:00:00"      # 51 days before ref → outside 30d
        _write(tmp_path / "run-01.xml", _make_suite_xml([("t", "X", True, False)], timestamp=recent_ts))
        _write(tmp_path / "run-02.xml", _make_suite_xml([("t", "X", True, False)], timestamp=old_ts))
        result = parse_junit_directory(str(tmp_path), reference_date=ref)
        assert result["X::t"].failure_count_last_30d == 1   # only the recent one
        assert result["X::t"].total_runs == 2               # both counted for total

    def test_no_timestamps_failure_count_equals_all_failures(self, tmp_path):
        _write(tmp_path / "run-01.xml", _make_suite_xml([("t", "X", True, False)]))
        _write(tmp_path / "run-02.xml", _make_suite_xml([("t", "X", True, False)]))
        result = parse_junit_directory(str(tmp_path))
        assert result["X::t"].failure_count_last_30d == 2

    def test_missing_timestamp_run_included_conservatively(self, tmp_path):
        # run-01: timestamped old → excluded by date filter
        # run-02: no timestamp → included conservatively
        ref = datetime.date(2026, 4, 21)
        old_ts = "2026-02-01T00:00:00"   # 79 days ago → outside 30d
        _write(tmp_path / "run-01.xml", _make_suite_xml([("t", "X", True, False)], timestamp=old_ts))
        _write(tmp_path / "run-02.xml", _make_suite_xml([("t", "X", True, False)]))  # no timestamp
        result = parse_junit_directory(str(tmp_path), reference_date=ref)
        assert result["X::t"].failure_count_last_30d == 1   # run-02 only (old is excluded)

    # --- error cases ---

    def test_malformed_xml_raises_input_validation_error(self, tmp_path):
        _write(tmp_path / "bad.xml", "<not closed")
        with pytest.raises(InputValidationError, match="Malformed XML"):
            parse_junit_directory(str(tmp_path))

    def test_malformed_xml_error_includes_filename(self, tmp_path):
        _write(tmp_path / "broken-run.xml", "<unclosed>")
        with pytest.raises(InputValidationError, match="broken-run.xml"):
            parse_junit_directory(str(tmp_path))

    def test_failure_adjacent_to_pass_is_flaky(self, tmp_path):
        # fail, pass → run 1 fails and run 2 passes → run 1 is a flaky occurrence
        _write(tmp_path / "run-01.xml", _make_suite_xml([("t", "X", True, False)]))
        _write(tmp_path / "run-02.xml", _make_suite_xml([("t", "X", False, False)]))
        result = parse_junit_directory(str(tmp_path))
        assert result["X::t"].flakiness_rate == pytest.approx(1 / 2)
        assert result["X::t"].total_runs == 2

    def test_isolated_failure_between_passes_is_flaky(self, tmp_path):
        # pass, fail, pass → run 2 fails between passes → flaky occurrence
        _write(tmp_path / "run-01.xml", _make_suite_xml([("t", "X", False, False)]))
        _write(tmp_path / "run-02.xml", _make_suite_xml([("t", "X", True, False)]))
        _write(tmp_path / "run-03.xml", _make_suite_xml([("t", "X", False, False)]))
        result = parse_junit_directory(str(tmp_path))
        assert result["X::t"].flakiness_rate == pytest.approx(1 / 3)
        assert result["X::t"].total_runs == 3

    def test_unparseable_timestamp_treated_as_no_timestamp(self, tmp_path):
        # Non-ISO timestamp → _parse_timestamp returns None → run included in last_30d
        ref = datetime.date(2026, 4, 21)
        xml = _make_suite_xml([("t", "X", True, False)], timestamp="not-a-date")
        _write(tmp_path / "run-01.xml", xml)
        result = parse_junit_directory(str(tmp_path), reference_date=ref)
        # No parseable date → treated conservatively as "no timestamp" → included
        assert result["X::t"].failure_count_last_30d == 1

    def test_unknown_root_tag_falls_back_to_iter_testsuite(self, tmp_path):
        # Root tag that is neither testsuite nor testsuites — graceful fallback
        root = ET.Element("results")
        suite = ET.SubElement(root, "testsuite")
        suite.set("name", "T")
        tc = ET.SubElement(suite, "testcase")
        tc.set("name", "test_z")
        tc.set("classname", "Pkg")
        _write(tmp_path / "odd.xml", ET.tostring(root, encoding="unicode"))
        result = parse_junit_directory(str(tmp_path))
        assert "Pkg::test_z" in result
