"""B1 — diff_mapper tests (written RED before implementation)."""
from __future__ import annotations

import pytest
import yaml

from intelligent_regression_optimizer.diff_mapper import (
    AreaMapping,
    load_area_map,
    map_files_to_areas,
    parse_diff_output,
)
from intelligent_regression_optimizer.input_loader import InputValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_area_map(tmp_path, mappings: list[dict]) -> str:
    p = tmp_path / "area-map.yaml"
    p.write_text(yaml.safe_dump({"mappings": mappings}))
    return str(p)


# ---------------------------------------------------------------------------
# AreaMapping dataclass
# ---------------------------------------------------------------------------

class TestAreaMapping:
    def test_fields_accessible(self):
        m = AreaMapping(pattern="src/payments/**", areas=["PaymentService"])
        assert m.pattern == "src/payments/**"
        assert m.areas == ["PaymentService"]

    def test_empty_areas_allowed(self):
        m = AreaMapping(pattern="tests/**", areas=[])
        assert m.areas == []


# ---------------------------------------------------------------------------
# load_area_map — valid cases
# ---------------------------------------------------------------------------

class TestLoadAreaMapValid:
    def test_single_mapping(self, tmp_path):
        path = _write_area_map(tmp_path, [
            {"pattern": "src/payments/**", "areas": ["PaymentService"]},
        ])
        result = load_area_map(path)
        assert len(result) == 1
        assert result[0].pattern == "src/payments/**"
        assert result[0].areas == ["PaymentService"]

    def test_multiple_mappings(self, tmp_path):
        path = _write_area_map(tmp_path, [
            {"pattern": "src/payments/**", "areas": ["PaymentService"]},
            {"pattern": "src/orders/**", "areas": ["OrderFacade", "OrderService"]},
        ])
        result = load_area_map(path)
        assert len(result) == 2
        assert result[1].areas == ["OrderFacade", "OrderService"]

    def test_empty_areas_entry_allowed(self, tmp_path):
        path = _write_area_map(tmp_path, [
            {"pattern": "tests/**", "areas": []},
        ])
        result = load_area_map(path)
        assert result[0].areas == []

    def test_empty_mappings_list_returns_empty(self, tmp_path):
        path = _write_area_map(tmp_path, [])
        result = load_area_map(path)
        assert result == []

    def test_order_preserved(self, tmp_path):
        path = _write_area_map(tmp_path, [
            {"pattern": "src/a/**", "areas": ["A"]},
            {"pattern": "src/b/**", "areas": ["B"]},
            {"pattern": "src/c/**", "areas": ["C"]},
        ])
        result = load_area_map(path)
        assert [m.pattern for m in result] == ["src/a/**", "src/b/**", "src/c/**"]


# ---------------------------------------------------------------------------
# load_area_map — error cases
# ---------------------------------------------------------------------------

class TestLoadAreaMapErrors:
    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(InputValidationError, match="not found"):
            load_area_map(str(tmp_path / "no-such-file.yaml"))

    def test_not_a_mapping_at_root_raises(self, tmp_path):
        p = tmp_path / "area-map.yaml"
        p.write_text("- item1\n- item2\n")
        with pytest.raises(InputValidationError, match="mapping"):
            load_area_map(str(p))

    def test_missing_mappings_key_raises(self, tmp_path):
        p = tmp_path / "area-map.yaml"
        p.write_text("patterns: []\n")
        with pytest.raises(InputValidationError, match="mappings"):
            load_area_map(str(p))

    def test_mappings_not_a_list_raises(self, tmp_path):
        p = tmp_path / "area-map.yaml"
        p.write_text("mappings: not-a-list\n")
        with pytest.raises(InputValidationError, match="mappings"):
            load_area_map(str(p))

    def test_entry_missing_pattern_raises(self, tmp_path):
        path = _write_area_map(tmp_path, [
            {"areas": ["PaymentService"]},
        ])
        with pytest.raises(InputValidationError, match="pattern"):
            load_area_map(path)

    def test_entry_missing_areas_raises(self, tmp_path):
        path = _write_area_map(tmp_path, [
            {"pattern": "src/payments/**"},
        ])
        with pytest.raises(InputValidationError, match="areas"):
            load_area_map(path)

    def test_areas_not_a_list_raises(self, tmp_path):
        path = _write_area_map(tmp_path, [
            {"pattern": "src/payments/**", "areas": "PaymentService"},
        ])
        with pytest.raises(InputValidationError, match="areas"):
            load_area_map(path)

    def test_pattern_not_a_string_raises(self, tmp_path):
        path = _write_area_map(tmp_path, [
            {"pattern": 123, "areas": ["A"]},
        ])
        with pytest.raises(InputValidationError, match="pattern"):
            load_area_map(path)

    def test_malformed_yaml_raises(self, tmp_path):
        p = tmp_path / "area-map.yaml"
        p.write_text("mappings: [\n  {bad yaml\n")
        with pytest.raises(InputValidationError, match="parse"):
            load_area_map(str(p))

    def test_entry_not_a_dict_raises(self, tmp_path):
        p = tmp_path / "area-map.yaml"
        p.write_text("mappings:\n  - just-a-string\n")
        with pytest.raises(InputValidationError, match="mapping"):
            load_area_map(str(p))


# ---------------------------------------------------------------------------
# parse_diff_output
# ---------------------------------------------------------------------------

class TestParseDiffOutput:
    def test_single_file(self):
        assert parse_diff_output("src/payments/service.py\n") == ["src/payments/service.py"]

    def test_multiple_files(self):
        text = "src/payments/service.py\nsrc/orders/facade.py\n"
        assert parse_diff_output(text) == ["src/payments/service.py", "src/orders/facade.py"]

    def test_empty_string_returns_empty(self):
        assert parse_diff_output("") == []

    def test_blank_lines_ignored(self):
        text = "src/a.py\n\nsrc/b.py\n\n"
        assert parse_diff_output(text) == ["src/a.py", "src/b.py"]

    def test_windows_line_endings(self):
        text = "src/payments/service.py\r\nsrc/orders/facade.py\r\n"
        assert parse_diff_output(text) == ["src/payments/service.py", "src/orders/facade.py"]

    def test_whitespace_only_lines_ignored(self):
        text = "src/a.py\n   \nsrc/b.py\n"
        assert parse_diff_output(text) == ["src/a.py", "src/b.py"]


# ---------------------------------------------------------------------------
# map_files_to_areas
# ---------------------------------------------------------------------------

class TestMapFilesToAreas:
    def _mappings(self, specs: list[tuple[str, list[str]]]) -> list[AreaMapping]:
        return [AreaMapping(pattern=p, areas=a) for p, a in specs]

    def test_single_file_single_match(self):
        mappings = self._mappings([("src/payments/**", ["PaymentService"])])
        result = map_files_to_areas(["src/payments/service.py"], mappings)
        assert result == {"PaymentService"}

    def test_multiple_files_different_areas(self):
        mappings = self._mappings([
            ("src/payments/**", ["PaymentService"]),
            ("src/orders/**", ["OrderFacade"]),
        ])
        result = map_files_to_areas(
            ["src/payments/service.py", "src/orders/facade.py"], mappings
        )
        assert result == {"PaymentService", "OrderFacade"}

    def test_file_matches_multiple_patterns_union(self):
        """A file matching two patterns contributes areas from both."""
        mappings = self._mappings([
            ("src/payments/**", ["PaymentService"]),
            ("src/**", ["AllBackend"]),
        ])
        result = map_files_to_areas(["src/payments/service.py"], mappings)
        assert result == {"PaymentService", "AllBackend"}

    def test_empty_areas_pattern_contributes_nothing(self):
        mappings = self._mappings([
            ("tests/**", []),
            ("src/payments/**", ["PaymentService"]),
        ])
        result = map_files_to_areas(
            ["tests/test_service.py", "src/payments/service.py"], mappings
        )
        assert result == {"PaymentService"}

    def test_no_match_returns_empty(self):
        mappings = self._mappings([("src/payments/**", ["PaymentService"])])
        result = map_files_to_areas(["docs/README.md"], mappings)
        assert result == set()

    def test_empty_files_list_returns_empty(self):
        mappings = self._mappings([("src/**", ["Backend"])])
        assert map_files_to_areas([], mappings) == set()

    def test_empty_mappings_returns_empty(self):
        assert map_files_to_areas(["src/a.py"], []) == set()

    def test_glob_star_matches_subdirectories(self):
        mappings = self._mappings([("src/payments/**", ["PaymentService"])])
        result = map_files_to_areas(["src/payments/v2/gateway.py"], mappings)
        assert result == {"PaymentService"}

    def test_glob_question_mark(self):
        mappings = self._mappings([("src/?.py", ["ShortModule"])])
        result = map_files_to_areas(["src/a.py"], mappings)
        assert result == {"ShortModule"}

    def test_exact_path_match(self):
        mappings = self._mappings([("src/config.py", ["Config"])])
        result = map_files_to_areas(["src/config.py"], mappings)
        assert result == {"Config"}

    def test_duplicate_areas_deduplicated(self):
        """Two patterns matching the same file with the same area → single entry."""
        mappings = self._mappings([
            ("src/payments/**", ["PaymentService"]),
            ("src/payments/service.py", ["PaymentService"]),
        ])
        result = map_files_to_areas(["src/payments/service.py"], mappings)
        assert result == {"PaymentService"}

    def test_result_is_set_not_list(self):
        mappings = self._mappings([("src/**", ["Backend"])])
        result = map_files_to_areas(["src/a.py"], mappings)
        assert isinstance(result, set)
