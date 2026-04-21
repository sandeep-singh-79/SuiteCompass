"""Loaders for pre-computed test history in CSV and JSON formats."""
from __future__ import annotations

import csv
import json
import pathlib

from intelligent_regression_optimizer.input_loader import InputValidationError
from intelligent_regression_optimizer.models import TestHistoryRecord

# ---------------------------------------------------------------------------
# Required columns
# ---------------------------------------------------------------------------

_REQUIRED_COLUMNS = {"test_id", "flakiness_rate", "failure_count_last_30d", "total_runs"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_record(
    test_id: str,
    flakiness_rate: float,
    failure_count_last_30d: int,
    total_runs: int,
    source: str,
) -> None:
    if not (0.0 <= flakiness_rate <= 1.0):
        raise InputValidationError(
            f"flakiness_rate must be between 0.0 and 1.0 for test_id={test_id!r} "
            f"in {source}, got {flakiness_rate!r}"
        )
    if failure_count_last_30d < 0:
        raise InputValidationError(
            f"failure_count_last_30d must be a non-negative integer for test_id={test_id!r} "
            f"in {source}, got {failure_count_last_30d!r}"
        )


def _check_required_columns(columns: set[str], source: str) -> None:
    missing = _REQUIRED_COLUMNS - columns
    if missing:
        missing_sorted = sorted(missing)
        raise InputValidationError(
            f"Missing required column(s) {missing_sorted} in {source}"
        )


def _add_record(
    result: dict[str, TestHistoryRecord],
    record: TestHistoryRecord,
    source: str,
) -> None:
    if record.test_id in result:
        raise InputValidationError(
            f"duplicate test_id {record.test_id!r} in {source}"
        )
    result[record.test_id] = record


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_history_csv(path: str) -> dict[str, TestHistoryRecord]:
    """Load pre-computed test history from a CSV file.

    Returns a dict mapping test_id → TestHistoryRecord.
    Raises InputValidationError on schema or value violations.
    """
    p = pathlib.Path(path)
    if not p.exists():
        raise InputValidationError(f"History file not found: {path!r}")

    content = p.read_text(encoding="utf-8").strip()
    if not content:
        return {}

    source = p.name
    result: dict[str, TestHistoryRecord] = {}

    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return {}
        _check_required_columns(set(reader.fieldnames), source)

        for row in reader:
            test_id = row["test_id"]

            try:
                flakiness_rate = float(row["flakiness_rate"])
            except (ValueError, TypeError):
                raise InputValidationError(
                    f"flakiness_rate must be numeric for test_id={test_id!r} "
                    f"in {source}, got {row['flakiness_rate']!r}"
                )

            try:
                failure_count_last_30d = int(row["failure_count_last_30d"])
            except (ValueError, TypeError):
                raise InputValidationError(
                    f"failure_count_last_30d must be an integer for test_id={test_id!r} "
                    f"in {source}, got {row['failure_count_last_30d']!r}"
                )

            try:
                total_runs = int(row["total_runs"])
            except (ValueError, TypeError):
                raise InputValidationError(
                    f"total_runs must be an integer for test_id={test_id!r} "
                    f"in {source}, got {row['total_runs']!r}"
                )

            _validate_record(test_id, flakiness_rate, failure_count_last_30d, total_runs, source)

            last_run_date: str | None = row.get("last_run_date") or None

            record = TestHistoryRecord(
                test_id=test_id,
                flakiness_rate=flakiness_rate,
                failure_count_last_30d=failure_count_last_30d,
                total_runs=total_runs,
                last_run_date=last_run_date,
            )
            _add_record(result, record, source)

    return result


def load_history_json(path: str) -> dict[str, TestHistoryRecord]:
    """Load pre-computed test history from a JSON file.

    The file must contain a JSON array of objects, each with required fields:
    test_id, flakiness_rate, failure_count_last_30d, total_runs.
    Optional field: last_run_date.

    Returns a dict mapping test_id → TestHistoryRecord.
    Raises InputValidationError on schema, parse, or value violations.
    """
    p = pathlib.Path(path)
    if not p.exists():
        raise InputValidationError(f"History file not found: {path!r}")

    source = p.name
    raw_text = p.read_text(encoding="utf-8")

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise InputValidationError(
            f"Failed to parse JSON history file {source!r}: {exc}"
        ) from exc

    if not isinstance(data, list):
        raise InputValidationError(
            f"JSON history file {source!r} must contain a list at the top level, "
            f"got {type(data).__name__}"
        )

    if not data:
        return {}

    # Validate required keys using the first record's key set (treat as schema)
    first_keys = set(data[0].keys()) if data else set()
    _check_required_columns(first_keys, source)

    result: dict[str, TestHistoryRecord] = {}

    for i, entry in enumerate(data):
        _check_required_columns(set(entry.keys()), f"{source}[{i}]")

        test_id = entry["test_id"]

        try:
            flakiness_rate = float(entry["flakiness_rate"])
        except (ValueError, TypeError):
            raise InputValidationError(
                f"flakiness_rate must be numeric for test_id={test_id!r} "
                f"in {source}[{i}], got {entry['flakiness_rate']!r}"
            )

        try:
            failure_count_last_30d = int(entry["failure_count_last_30d"])
        except (ValueError, TypeError):
            raise InputValidationError(
                f"failure_count_last_30d must be an integer for test_id={test_id!r} "
                f"in {source}[{i}], got {entry['failure_count_last_30d']!r}"
            )

        try:
            total_runs = int(entry["total_runs"])
        except (ValueError, TypeError):
            raise InputValidationError(
                f"total_runs must be an integer for test_id={test_id!r} "
                f"in {source}[{i}], got {entry['total_runs']!r}"
            )

        _validate_record(test_id, flakiness_rate, failure_count_last_30d, total_runs, source)

        last_run_date: str | None = entry.get("last_run_date") or None

        record = TestHistoryRecord(
            test_id=test_id,
            flakiness_rate=flakiness_rate,
            failure_count_last_30d=failure_count_last_30d,
            total_runs=total_runs,
            last_run_date=last_run_date,
        )
        _add_record(result, record, source)

    return result
