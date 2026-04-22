"""JUnit XML parser — derives test history metrics from CI run artifacts.

Parses all *.xml files in a directory (each file = one test run) and computes
per-test flakiness_rate, failure_count_last_30d, and total_runs.

Supports:
- pytest-junit: <testsuite> at root
- surefire: <testsuites> wrapping <testsuite> children
"""
from __future__ import annotations

import collections
import datetime
import pathlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from intelligent_regression_optimizer.input_loader import InputValidationError
from intelligent_regression_optimizer.models import TestHistoryRecord


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class _RunEntry:
    """Outcome of a single test inside a single run file."""

    failed: bool
    run_date: datetime.date | None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_timestamp(ts: str) -> datetime.date | None:
    """Parse an ISO-ish timestamp string from a <testsuite> attribute.

    Accepts: "2026-04-15T10:00:00", "2026-04-15T10:00:00.000", "2026-04-15".
    Returns None when the string is empty or unparseable.
    """
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(ts, fmt).date()
        except ValueError:
            continue
    return None


def _make_test_id(classname: str | None, name: str) -> str:
    """Build a stable test identifier.

    Uses pytest-style "classname::name" when classname is present;
    falls back to plain name otherwise.
    """
    if classname:
        return f"{classname}::{name}"
    return name


def _extract_from_suite(suite: ET.Element) -> list[tuple[str, _RunEntry]]:
    """Extract [(test_id, RunEntry)] from a <testsuite> element."""
    suite_date = _parse_timestamp(suite.get("timestamp") or "")
    entries: list[tuple[str, _RunEntry]] = []

    for tc in suite.findall("testcase"):
        # Skipped tests contribute nothing to the history
        if tc.find("skipped") is not None:
            continue

        name = tc.get("name") or ""
        classname = tc.get("classname") or None
        failed = tc.find("failure") is not None or tc.find("error") is not None

        test_id = _make_test_id(classname, name)
        entries.append((test_id, _RunEntry(failed=failed, run_date=suite_date)))

    return entries


def _extract_from_root(root: ET.Element) -> list[tuple[str, _RunEntry]]:
    """Dispatch on root tag and extract all (test_id, RunEntry) pairs."""
    results: list[tuple[str, _RunEntry]] = []

    if root.tag == "testsuites":
        suites = root.findall("testsuite")
    elif root.tag == "testsuite":
        suites = [root]
    else:
        # Graceful fallback: find any testsuite elements in the tree
        suites = list(root.iter("testsuite"))

    for suite in suites:
        results.extend(_extract_from_suite(suite))

    return results


def _compute_flakiness_rate(entries: list[_RunEntry]) -> float:
    """Return the fraction of runs that exhibit flaky behaviour.

    A failure is counted as *flaky* when at least one adjacent run (prev or
    next by file order) was a pass.  Consistent failures have no adjacent pass
    and therefore contribute 0 to the numerator.

    ``entries`` are assumed to be in lexicographic file order, which is treated
    as chronological order.  Callers must ensure this ordering holds for the
    heuristic to be meaningful.
    """
    total = len(entries)
    if total == 0:
        return 0.0
    flaky = 0
    for i, entry in enumerate(entries):
        if not entry.failed:
            continue
        prev_passed = i > 0 and not entries[i - 1].failed
        next_passed = i < total - 1 and not entries[i + 1].failed
        if prev_passed or next_passed:
            flaky += 1
    return flaky / total


def parse_junit_directory(
    dir_path: str,
    reference_date: datetime.date | None = None,
) -> dict[str, TestHistoryRecord]:
    """Parse all JUnit XML files in a directory and compute per-test history metrics.

    Each *.xml file is treated as one test run. Files that do not end in .xml are
    ignored. Subdirectories are not traversed.

    Metrics computed per test:
    - total_runs: number of runs in which the test appeared (skipped excluded)
    - flakiness_rate: fraction of runs that are *flaky* (failure adjacent to a
      pass in the sorted-by-filename run sequence, which is treated as
      chronological order — consistent failures score 0.0)
    - failure_count_last_30d: failures from runs within 30 days of reference_date;
      runs without a parseable timestamp are included conservatively

    Args:
        dir_path: path to directory containing JUnit XML files.
        reference_date: anchor date for the 30-day window. Defaults to today.

    Returns:
        dict mapping test_id → TestHistoryRecord.

    Raises:
        InputValidationError: if dir_path does not exist or any XML file is malformed.
    """
    p = pathlib.Path(dir_path)
    if not p.is_dir():
        raise InputValidationError(f"History directory not found: {dir_path!r}")

    if reference_date is None:
        reference_date = datetime.date.today()

    cutoff_date = reference_date - datetime.timedelta(days=30)

    xml_files = sorted(p.glob("*.xml"))
    if not xml_files:
        return {}

    # Accumulator: test_id → list of run entries across all files
    accumulator: dict[str, list[_RunEntry]] = collections.defaultdict(list)

    for xml_file in xml_files:
        try:
            tree = ET.parse(xml_file)
        except ET.ParseError as exc:
            raise InputValidationError(
                f"Malformed XML in {xml_file.name!r}: {exc}"
            ) from exc

        root = tree.getroot()
        for test_id, entry in _extract_from_root(root):
            accumulator[test_id].append(entry)

    result: dict[str, TestHistoryRecord] = {}

    for test_id, entries in accumulator.items():
        total_runs = len(entries)
        flakiness_rate = _compute_flakiness_rate(entries)

        # Include failures from runs that are: (a) within 30 days OR (b) have no timestamp
        failure_count_last_30d = sum(
            1
            for e in entries
            if e.failed and (e.run_date is None or e.run_date >= cutoff_date)
        )

        result[test_id] = TestHistoryRecord(
            test_id=test_id,
            flakiness_rate=flakiness_rate,
            failure_count_last_30d=failure_count_last_30d,
            total_runs=total_runs,
        )

    return result
