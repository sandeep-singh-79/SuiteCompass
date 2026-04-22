"""B2 — diff-areas subcommand + iro run --area-map tests (written RED)."""
from __future__ import annotations

import yaml
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from intelligent_regression_optimizer.cli import main
from intelligent_regression_optimizer.models import EXIT_OK


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_area_map(tmp_path, mappings: list[dict]) -> Path:
    p = tmp_path / "area-map.yaml"
    p.write_text(yaml.safe_dump({"mappings": mappings}))
    return p


def _write_input(tmp_path, areas: list[str] | None = None) -> Path:
    data = {
        "sprint_context": {
            "stories": [
                {
                    "id": "S-1",
                    "risk": "high",
                    "changed_areas": areas or ["PaymentService"],
                }
            ],
        },
        "test_suite": [
            {
                "id": "T-001",
                "name": "Payment test",
                "layer": "unit",
                "coverage_areas": ["PaymentService"],
                "execution_time_secs": 5,
                "flakiness_rate": 0.0,
                "automated": True,
            }
        ],
        "constraints": {},
    }
    p = tmp_path / "input.yaml"
    p.write_text(yaml.safe_dump(data))
    return p


# ---------------------------------------------------------------------------
# iro diff-areas — diff-file mode (no subprocess needed)
# ---------------------------------------------------------------------------

class TestDiffAreasCommand:
    def test_diff_file_mode_exits_0(self, tmp_path):
        area_map = _write_area_map(tmp_path, [
            {"pattern": "src/payments/**", "areas": ["PaymentService"]},
        ])
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("src/payments/service.py\n")
        runner = CliRunner()
        result = runner.invoke(main, [
            "diff-areas",
            "--area-map", str(area_map),
            "--diff-file", str(diff_file),
        ])
        assert result.exit_code == 0

    def test_diff_file_outputs_yaml_fragment(self, tmp_path):
        area_map = _write_area_map(tmp_path, [
            {"pattern": "src/payments/**", "areas": ["PaymentService"]},
        ])
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("src/payments/service.py\n")
        runner = CliRunner()
        result = runner.invoke(main, [
            "diff-areas",
            "--area-map", str(area_map),
            "--diff-file", str(diff_file),
        ])
        assert "changed_areas" in result.output
        assert "PaymentService" in result.output

    def test_diff_file_multiple_areas(self, tmp_path):
        area_map = _write_area_map(tmp_path, [
            {"pattern": "src/payments/**", "areas": ["PaymentService"]},
            {"pattern": "src/orders/**", "areas": ["OrderFacade"]},
        ])
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("src/payments/service.py\nsrc/orders/facade.py\n")
        runner = CliRunner()
        result = runner.invoke(main, [
            "diff-areas",
            "--area-map", str(area_map),
            "--diff-file", str(diff_file),
        ])
        assert "PaymentService" in result.output
        assert "OrderFacade" in result.output

    def test_diff_file_no_matches_outputs_empty_list(self, tmp_path):
        area_map = _write_area_map(tmp_path, [
            {"pattern": "src/payments/**", "areas": ["PaymentService"]},
        ])
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("docs/README.md\n")
        runner = CliRunner()
        result = runner.invoke(main, [
            "diff-areas",
            "--area-map", str(area_map),
            "--diff-file", str(diff_file),
        ])
        assert result.exit_code == 0
        assert "changed_areas" in result.output

    def test_diff_file_empty_diff_outputs_empty_list(self, tmp_path):
        area_map = _write_area_map(tmp_path, [
            {"pattern": "src/**", "areas": ["Backend"]},
        ])
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("")
        runner = CliRunner()
        result = runner.invoke(main, [
            "diff-areas",
            "--area-map", str(area_map),
            "--diff-file", str(diff_file),
        ])
        assert result.exit_code == 0
        assert "changed_areas" in result.output

    def test_missing_area_map_exits_2(self, tmp_path):
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("src/a.py\n")
        runner = CliRunner()
        result = runner.invoke(main, [
            "diff-areas",
            "--area-map", str(tmp_path / "no-such-map.yaml"),
            "--diff-file", str(diff_file),
        ])
        assert result.exit_code == 2

    def test_missing_diff_file_exits_2(self, tmp_path):
        area_map = _write_area_map(tmp_path, [{"pattern": "src/**", "areas": ["A"]}])
        runner = CliRunner()
        result = runner.invoke(main, [
            "diff-areas",
            "--area-map", str(area_map),
            "--diff-file", str(tmp_path / "no-diff.txt"),
        ])
        assert result.exit_code == 2

    def test_area_map_schema_error_exits_2(self, tmp_path):
        bad_map = tmp_path / "area-map.yaml"
        bad_map.write_text("mappings:\n  - {areas: [A]}\n")   # missing 'pattern'
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("src/a.py\n")
        runner = CliRunner()
        result = runner.invoke(main, [
            "diff-areas",
            "--area-map", str(bad_map),
            "--diff-file", str(diff_file),
        ])
        assert result.exit_code == 2

    def test_no_flags_exits_2(self):
        """diff-areas requires --area-map; missing it should exit 2."""
        runner = CliRunner()
        result = runner.invoke(main, ["diff-areas"])
        assert result.exit_code == 2

    def test_area_map_only_no_diff_source_exits_2(self, tmp_path):
        """--area-map without --diff-file or --ref must exit 2 (explicit diff source required)."""
        area_map = _write_area_map(tmp_path, [{"pattern": "src/**", "areas": ["A"]}])
        runner = CliRunner()
        result = runner.invoke(main, [
            "diff-areas",
            "--area-map", str(area_map),
        ])
        assert result.exit_code == 2

    def test_git_ref_mode_calls_subprocess(self, tmp_path):
        """--ref mode calls subprocess; mock it to avoid git dependency."""
        area_map = _write_area_map(tmp_path, [
            {"pattern": "src/payments/**", "areas": ["PaymentService"]},
        ])
        with patch(
            "intelligent_regression_optimizer.cli.subprocess.run"
        ) as mock_run:
            mock_run.return_value.stdout = "src/payments/service.py\n"
            mock_run.return_value.returncode = 0
            runner = CliRunner()
            result = runner.invoke(main, [
                "diff-areas",
                "--area-map", str(area_map),
                "--ref", "HEAD~1",
            ])
        assert result.exit_code == 0
        assert "PaymentService" in result.output

    def test_git_ref_mode_git_failure_exits_2(self, tmp_path):
        """If git subprocess fails (returncode != 0), exit 2."""
        area_map = _write_area_map(tmp_path, [
            {"pattern": "src/**", "areas": ["A"]},
        ])
        with patch(
            "intelligent_regression_optimizer.cli.subprocess.run"
        ) as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 128
            runner = CliRunner()
            result = runner.invoke(main, [
                "diff-areas",
                "--area-map", str(area_map),
                "--ref", "HEAD~1",
            ])
        assert result.exit_code == 2

    def test_diff_file_and_ref_mutually_exclusive(self, tmp_path):
        area_map = _write_area_map(tmp_path, [{"pattern": "src/**", "areas": ["A"]}])
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("src/a.py\n")
        runner = CliRunner()
        result = runner.invoke(main, [
            "diff-areas",
            "--area-map", str(area_map),
            "--diff-file", str(diff_file),
            "--ref", "HEAD~1",
        ])
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# iro run --area-map + --ref integration
# ---------------------------------------------------------------------------

class TestRunWithAreaMap:
    def test_run_area_map_with_diff_file_exits_0(self, tmp_path):
        area_map = _write_area_map(tmp_path, [
            {"pattern": "src/payments/**", "areas": ["PaymentService"]},
        ])
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("src/payments/service.py\n")
        input_p = _write_input(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", str(input_p),
            "--area-map", str(area_map),
            "--diff-file", str(diff_file),
        ])
        assert result.exit_code == 0

    def test_run_area_map_overrides_story_changed_areas(self, tmp_path):
        """Areas from diff should replace the manual changed_areas in the YAML."""
        area_map = _write_area_map(tmp_path, [
            {"pattern": "src/orders/**", "areas": ["OrderFacade"]},
        ])
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("src/orders/service.py\n")
        # YAML has PaymentService; diff says OrderFacade
        input_p = _write_input(tmp_path, areas=["PaymentService"])
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", str(input_p),
            "--area-map", str(area_map),
            "--diff-file", str(diff_file),
        ])
        assert result.exit_code == 0

    def test_run_area_map_missing_file_exits_2(self, tmp_path):
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("src/a.py\n")
        input_p = _write_input(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", str(input_p),
            "--area-map", str(tmp_path / "no-map.yaml"),
            "--diff-file", str(diff_file),
        ])
        assert result.exit_code == 2

    def test_run_area_map_requires_diff_source(self, tmp_path):
        """--area-map without --diff-file or --ref should exit 2."""
        area_map = _write_area_map(tmp_path, [{"pattern": "src/**", "areas": ["A"]}])
        input_p = _write_input(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", str(input_p),
            "--area-map", str(area_map),
        ])
        assert result.exit_code == 2
