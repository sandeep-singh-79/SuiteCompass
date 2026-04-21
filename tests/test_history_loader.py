"""Unit tests for history_loader.py — written RED before implementation (TDD A1)."""
from __future__ import annotations

import csv
import json
import pathlib

import pytest

from intelligent_regression_optimizer.input_loader import InputValidationError
from intelligent_regression_optimizer.models import TestHistoryRecord
from intelligent_regression_optimizer.history_loader import (
    load_history_csv,
    load_history_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: pathlib.Path, data: object) -> None:
    path.write_text(json.dumps(data))


# ---------------------------------------------------------------------------
# TestHistoryRecord model
# ---------------------------------------------------------------------------

class TestHistoryRecordModel:
    def test_required_fields_stored(self):
        r = TestHistoryRecord(
            test_id="T-001",
            flakiness_rate=0.25,
            failure_count_last_30d=3,
            total_runs=100,
        )
        assert r.test_id == "T-001"
        assert r.flakiness_rate == 0.25
        assert r.failure_count_last_30d == 3
        assert r.total_runs == 100

    def test_last_run_date_defaults_to_none(self):
        r = TestHistoryRecord(
            test_id="T-002",
            flakiness_rate=0.0,
            failure_count_last_30d=0,
            total_runs=10,
        )
        assert r.last_run_date is None

    def test_last_run_date_can_be_set(self):
        r = TestHistoryRecord(
            test_id="T-003",
            flakiness_rate=0.1,
            failure_count_last_30d=1,
            total_runs=50,
            last_run_date="2026-04-01",
        )
        assert r.last_run_date == "2026-04-01"

    def test_zero_flakiness_allowed(self):
        r = TestHistoryRecord(test_id="T-004", flakiness_rate=0.0, failure_count_last_30d=0, total_runs=5)
        assert r.flakiness_rate == 0.0

    def test_full_flakiness_allowed(self):
        r = TestHistoryRecord(test_id="T-005", flakiness_rate=1.0, failure_count_last_30d=10, total_runs=10)
        assert r.flakiness_rate == 1.0


# ---------------------------------------------------------------------------
# load_history_csv — valid cases
# ---------------------------------------------------------------------------

class TestLoadHistoryCsvValid:
    def test_single_row_returns_dict_keyed_by_test_id(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "0.2", "failure_count_last_30d": "4", "total_runs": "50"},
        ])
        result = load_history_csv(str(p))
        assert "T-001" in result
        rec = result["T-001"]
        assert isinstance(rec, TestHistoryRecord)
        assert rec.flakiness_rate == pytest.approx(0.2)
        assert rec.failure_count_last_30d == 4
        assert rec.total_runs == 50

    def test_multiple_rows(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "0.1", "failure_count_last_30d": "2", "total_runs": "20"},
            {"test_id": "T-002", "flakiness_rate": "0.5", "failure_count_last_30d": "10", "total_runs": "20"},
        ])
        result = load_history_csv(str(p))
        assert len(result) == 2
        assert "T-001" in result
        assert "T-002" in result

    def test_optional_last_run_date_loaded(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-003", "flakiness_rate": "0.0", "failure_count_last_30d": "0",
             "total_runs": "30", "last_run_date": "2026-03-15"},
        ])
        result = load_history_csv(str(p))
        assert result["T-003"].last_run_date == "2026-03-15"

    def test_missing_optional_last_run_date_is_none(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-004", "flakiness_rate": "0.3", "failure_count_last_30d": "3", "total_runs": "10"},
        ])
        result = load_history_csv(str(p))
        assert result["T-004"].last_run_date is None

    def test_zero_failure_count_allowed(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-005", "flakiness_rate": "0.0", "failure_count_last_30d": "0", "total_runs": "100"},
        ])
        result = load_history_csv(str(p))
        assert result["T-005"].failure_count_last_30d == 0


# ---------------------------------------------------------------------------
# load_history_csv — error cases
# ---------------------------------------------------------------------------

class TestLoadHistoryCsvErrors:
    def test_missing_test_id_column_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"flakiness_rate": "0.1", "failure_count_last_30d": "1", "total_runs": "10"},
        ])
        with pytest.raises(InputValidationError, match="test_id"):
            load_history_csv(str(p))

    def test_missing_flakiness_rate_column_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "failure_count_last_30d": "1", "total_runs": "10"},
        ])
        with pytest.raises(InputValidationError, match="flakiness_rate"):
            load_history_csv(str(p))

    def test_missing_failure_count_column_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "0.1", "total_runs": "10"},
        ])
        with pytest.raises(InputValidationError, match="failure_count_last_30d"):
            load_history_csv(str(p))

    def test_missing_total_runs_column_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "0.1", "failure_count_last_30d": "1"},
        ])
        with pytest.raises(InputValidationError, match="total_runs"):
            load_history_csv(str(p))

    def test_flakiness_above_1_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "1.5", "failure_count_last_30d": "1", "total_runs": "10"},
        ])
        with pytest.raises(InputValidationError, match="flakiness_rate"):
            load_history_csv(str(p))

    def test_flakiness_below_0_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "-0.1", "failure_count_last_30d": "1", "total_runs": "10"},
        ])
        with pytest.raises(InputValidationError, match="flakiness_rate"):
            load_history_csv(str(p))

    def test_negative_failure_count_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "0.1", "failure_count_last_30d": "-1", "total_runs": "10"},
        ])
        with pytest.raises(InputValidationError, match="failure_count_last_30d"):
            load_history_csv(str(p))

    def test_non_numeric_flakiness_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "high", "failure_count_last_30d": "1", "total_runs": "10"},
        ])
        with pytest.raises(InputValidationError, match="flakiness_rate"):
            load_history_csv(str(p))

    def test_duplicate_test_ids_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "0.1", "failure_count_last_30d": "1", "total_runs": "10"},
            {"test_id": "T-001", "flakiness_rate": "0.2", "failure_count_last_30d": "2", "total_runs": "10"},
        ])
        with pytest.raises(InputValidationError, match="duplicate"):
            load_history_csv(str(p))

    def test_empty_file_returns_empty_dict(self, tmp_path):
        p = tmp_path / "history.csv"
        p.write_text("")
        result = load_history_csv(str(p))
        assert result == {}

    def test_file_not_found_raises_input_validation_error(self, tmp_path):
        p = tmp_path / "nonexistent.csv"
        with pytest.raises(InputValidationError, match="not found"):
            load_history_csv(str(p))

    def test_non_numeric_failure_count_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "0.1", "failure_count_last_30d": "many", "total_runs": "10"},
        ])
        with pytest.raises(InputValidationError, match="failure_count_last_30d"):
            load_history_csv(str(p))

    def test_negative_total_runs_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "0.1", "failure_count_last_30d": "1", "total_runs": "-1"},
        ])
        with pytest.raises(InputValidationError, match="total_runs"):
            load_history_csv(str(p))

    def test_non_numeric_total_runs_raises(self, tmp_path):
        p = tmp_path / "history.csv"
        _write_csv(p, [
            {"test_id": "T-001", "flakiness_rate": "0.1", "failure_count_last_30d": "1", "total_runs": "lots"},
        ])
        with pytest.raises(InputValidationError, match="total_runs"):
            load_history_csv(str(p))

    def test_header_only_csv_returns_empty_dict(self, tmp_path):
        p = tmp_path / "history.csv"
        p.write_text("test_id,flakiness_rate,failure_count_last_30d,total_runs\n")
        result = load_history_csv(str(p))
        assert result == {}


# ---------------------------------------------------------------------------
# load_history_json — valid cases
# ---------------------------------------------------------------------------

class TestLoadHistoryJsonValid:
    def test_single_record(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [
            {"test_id": "T-001", "flakiness_rate": 0.2, "failure_count_last_30d": 4, "total_runs": 50},
        ])
        result = load_history_json(str(p))
        assert "T-001" in result
        rec = result["T-001"]
        assert rec.flakiness_rate == pytest.approx(0.2)
        assert rec.failure_count_last_30d == 4
        assert rec.total_runs == 50

    def test_multiple_records(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [
            {"test_id": "T-001", "flakiness_rate": 0.1, "failure_count_last_30d": 2, "total_runs": 20},
            {"test_id": "T-002", "flakiness_rate": 0.5, "failure_count_last_30d": 10, "total_runs": 20},
        ])
        result = load_history_json(str(p))
        assert len(result) == 2

    def test_optional_last_run_date_loaded(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [
            {"test_id": "T-003", "flakiness_rate": 0.0, "failure_count_last_30d": 0,
             "total_runs": 30, "last_run_date": "2026-03-15"},
        ])
        result = load_history_json(str(p))
        assert result["T-003"].last_run_date == "2026-03-15"

    def test_missing_optional_last_run_date_is_none(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [
            {"test_id": "T-004", "flakiness_rate": 0.3, "failure_count_last_30d": 3, "total_runs": 10},
        ])
        result = load_history_json(str(p))
        assert result["T-004"].last_run_date is None

    def test_empty_list_returns_empty_dict(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [])
        result = load_history_json(str(p))
        assert result == {}


# ---------------------------------------------------------------------------
# load_history_json — error cases
# ---------------------------------------------------------------------------

class TestLoadHistoryJsonErrors:
    def test_missing_test_id_raises(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [{"flakiness_rate": 0.1, "failure_count_last_30d": 1, "total_runs": 10}])
        with pytest.raises(InputValidationError, match="test_id"):
            load_history_json(str(p))

    def test_flakiness_above_1_raises(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [{"test_id": "T-001", "flakiness_rate": 1.5, "failure_count_last_30d": 1, "total_runs": 10}])
        with pytest.raises(InputValidationError, match="flakiness_rate"):
            load_history_json(str(p))

    def test_negative_failure_count_raises(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [{"test_id": "T-001", "flakiness_rate": 0.1, "failure_count_last_30d": -1, "total_runs": 10}])
        with pytest.raises(InputValidationError, match="failure_count_last_30d"):
            load_history_json(str(p))

    def test_duplicate_test_ids_raises(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [
            {"test_id": "T-001", "flakiness_rate": 0.1, "failure_count_last_30d": 1, "total_runs": 10},
            {"test_id": "T-001", "flakiness_rate": 0.2, "failure_count_last_30d": 2, "total_runs": 10},
        ])
        with pytest.raises(InputValidationError, match="duplicate"):
            load_history_json(str(p))

    def test_not_a_list_raises(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, {"test_id": "T-001", "flakiness_rate": 0.1})
        with pytest.raises(InputValidationError, match="list"):
            load_history_json(str(p))

    def test_malformed_json_raises(self, tmp_path):
        p = tmp_path / "history.json"
        p.write_text("{not valid json")
        with pytest.raises(InputValidationError, match="parse"):
            load_history_json(str(p))

    def test_file_not_found_raises(self, tmp_path):
        p = tmp_path / "nonexistent.json"
        with pytest.raises(InputValidationError, match="not found"):
            load_history_json(str(p))

    def test_non_numeric_failure_count_raises(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [{"test_id": "T-001", "flakiness_rate": 0.1, "failure_count_last_30d": "many", "total_runs": 10}])
        with pytest.raises(InputValidationError, match="failure_count_last_30d"):
            load_history_json(str(p))

    def test_negative_total_runs_raises(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [{"test_id": "T-001", "flakiness_rate": 0.1, "failure_count_last_30d": 1, "total_runs": -1}])
        with pytest.raises(InputValidationError, match="total_runs"):
            load_history_json(str(p))

    def test_non_numeric_total_runs_raises(self, tmp_path):
        p = tmp_path / "history.json"
        _write_json(p, [{"test_id": "T-001", "flakiness_rate": 0.1, "failure_count_last_30d": 1, "total_runs": "lots"}])
        with pytest.raises(InputValidationError, match="total_runs"):
            load_history_json(str(p))
