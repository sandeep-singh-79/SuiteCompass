"""T11 — CLI tests (written RED before implementation)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from intelligent_regression_optimizer.cli import main
from intelligent_regression_optimizer.models import EXIT_VALIDATION_ERROR, FlowResult


BENCHMARKS = Path(__file__).parent.parent / "benchmarks"
FIXTURES = Path(__file__).parent / "fixtures"


class TestRunCommand:
    """iro run <input.yaml> subcommand."""

    def test_run_valid_input_exits_0(self):
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(BENCHMARKS / "high-risk-feature-sprint.input.yaml")])
        assert result.exit_code == 0

    def test_run_valid_input_prints_markdown(self):
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(BENCHMARKS / "high-risk-feature-sprint.input.yaml")])
        assert "## Optimisation Summary" in result.output

    def test_run_missing_file_exits_2(self):
        runner = CliRunner()
        result = runner.invoke(main, ["run", "nonexistent-file.yaml"])
        assert result.exit_code == 2

    def test_run_invalid_input_exits_2(self, repo_tmp):
        bad = repo_tmp / "bad.yaml"
        bad.write_text("not_a_dict: yes\n")
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(bad)])
        assert result.exit_code == 2

    def test_run_output_flag_writes_file(self, repo_tmp):
        out_file = repo_tmp / "report.md"
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["run", str(BENCHMARKS / "high-risk-feature-sprint.input.yaml"), "--output", str(out_file)],
        )
        assert result.exit_code == 0
        assert out_file.exists()
        assert "## Optimisation Summary" in out_file.read_text()

    def test_run_all_three_benchmarks_exit_0(self):
        runner = CliRunner()
        for name in [
            "high-risk-feature-sprint.input.yaml",
            "low-risk-bugfix-sprint.input.yaml",
            "degraded-suite-high-flakiness.input.yaml",
        ]:
            result = runner.invoke(main, ["run", str(BENCHMARKS / name)])
            assert result.exit_code == 0, f"Failed on {name}: {result.output}"


class TestBenchmarkCommand:
    """iro benchmark <input.yaml> <assertions.yaml> subcommand."""

    def test_benchmark_passing_assertions_exits_0(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "benchmark",
                str(BENCHMARKS / "high-risk-feature-sprint.input.yaml"),
                str(BENCHMARKS / "high-risk-feature-sprint.assertions.yaml"),
            ],
        )
        assert result.exit_code == 0

    def test_benchmark_failing_assertions_exits_1(self, repo_tmp):
        failing = repo_tmp / "fail.assertions.yaml"
        failing.write_text("must_include_substrings:\n  - 'THIS_STRING_WILL_NEVER_APPEAR_XYZZY'\n")
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "benchmark",
                str(BENCHMARKS / "high-risk-feature-sprint.input.yaml"),
                str(failing),
            ],
        )
        assert result.exit_code == 1

    def test_benchmark_missing_input_exits_2(self):
        runner = CliRunner()
        result = runner.invoke(main, ["benchmark", "no-such-input.yaml", "no-such-assertions.yaml"])
        assert result.exit_code == 2

    def test_benchmark_missing_assertions_file_exits_2(self):
        """Valid input but non-existent assertions file should exit 2."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "benchmark",
                str(BENCHMARKS / "high-risk-feature-sprint.input.yaml"),
                "no-such-assertions.yaml",
            ],
        )
        assert result.exit_code == 2


class TestHelp:
    """Help text and guard-rail checks."""

    def test_no_args_shows_help(self):
        runner = CliRunner()
        result = runner.invoke(main, [])
        # Click returns exit code 0 for help display; output mentions subcommands
        assert "run" in result.output
        assert "benchmark" in result.output

    def test_help_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output


class TestValidationErrorPaths:
    """Covers EXIT_VALIDATION_ERROR branches in run and benchmark commands."""

    def test_run_validation_error_exits_1(self):
        bad_result = FlowResult(
            exit_code=EXIT_VALIDATION_ERROR,
            message="Output contract violated: ['Missing heading']",
            output_path=None,
        )
        runner = CliRunner()
        with patch("intelligent_regression_optimizer.cli.run_pipeline", return_value=bad_result):
            result = runner.invoke(main, ["run", "any.yaml"])
        assert result.exit_code == EXIT_VALIDATION_ERROR

    def test_benchmark_validation_error_exits_1(self):
        bad_result = FlowResult(
            exit_code=EXIT_VALIDATION_ERROR,
            message="Output contract violated: ['Missing heading']",
            output_path=None,
        )
        runner = CliRunner()
        with patch("intelligent_regression_optimizer.cli.run_pipeline", return_value=bad_result):
            result = runner.invoke(main, ["benchmark", "any.yaml", "any.assertions.yaml"])
        assert result.exit_code == EXIT_VALIDATION_ERROR


# ---------------------------------------------------------------------------
# A4: --history-dir and --history-file flags
# ---------------------------------------------------------------------------

class TestHistoryFlags:
    """iro run with --history-dir and --history-file flags."""

    def _minimal_input(self, tmp_path, test_id: str = "T-001", flakiness: float = 0.05) -> Path:
        """Write a minimal valid input YAML with one test and return its path."""
        import yaml
        data = {
            "sprint_context": {
                "stories": [{"id": "S-1", "risk": "low", "changed_areas": ["area-a"]}],
            },
            "test_suite": [
                {
                    "id": test_id,
                    "name": f"Test {test_id}",
                    "layer": "unit",
                    "coverage_areas": ["area-a"],
                    "execution_time_secs": 5,
                    "flakiness_rate": flakiness,
                    "automated": True,
                }
            ],
            "constraints": {"flakiness_retire_threshold": 0.30, "time_budget_mins": 60},
        }
        p = tmp_path / "input.yaml"
        p.write_text(yaml.safe_dump(data))
        return p

    def _write_junit_pass_fail(self, xml_dir: Path, test_id: str, n_pass: int, n_fail: int) -> None:
        """Write JUnit XML files for a single test — n_pass passing runs then n_fail failing."""
        import xml.etree.ElementTree as ET
        classname, name = test_id.split("::")
        run = 0
        for _ in range(n_pass):
            suite = ET.Element("testsuite")
            suite.set("name", "S")
            tc = ET.SubElement(suite, "testcase")
            tc.set("name", name)
            tc.set("classname", classname)
            p = xml_dir / f"run-{run:03d}.xml"
            p.write_text(ET.tostring(suite, encoding="unicode"))
            run += 1
        for _ in range(n_fail):
            suite = ET.Element("testsuite")
            suite.set("name", "S")
            tc = ET.SubElement(suite, "testcase")
            tc.set("name", name)
            tc.set("classname", classname)
            fl = ET.SubElement(tc, "failure")
            fl.set("message", "AssertionError")
            p = xml_dir / f"run-{run:03d}.xml"
            p.write_text(ET.tostring(suite, encoding="unicode"))
            run += 1

    # --- --history-dir ---

    def test_history_dir_flag_exits_0(self, tmp_path):
        xml_dir = tmp_path / "xml"
        xml_dir.mkdir()
        input_p = self._minimal_input(tmp_path, "Pkg::test_a", flakiness=0.1)
        self._write_junit_pass_fail(xml_dir, "Pkg::test_a", 3, 0)
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(input_p), "--history-dir", str(xml_dir)])
        assert result.exit_code == 0

    def test_history_dir_missing_exits_2(self, tmp_path):
        input_p = self._minimal_input(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(input_p), "--history-dir", str(tmp_path / "no-such-dir")])
        assert result.exit_code == 2

    def test_history_dir_empty_dir_exits_0(self, tmp_path):
        """Empty XML dir → no history available → pipeline still runs normally."""
        xml_dir = tmp_path / "xml"
        xml_dir.mkdir()
        input_p = self._minimal_input(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(input_p), "--history-dir", str(xml_dir)])
        assert result.exit_code == 0

    def test_history_dir_overlays_flakiness(self, tmp_path):
        """High-flakiness XML history should push test to retire tier."""
        xml_dir = tmp_path / "xml"
        xml_dir.mkdir()
        # Alternating pass/fail = highly flaky
        input_p = self._minimal_input(tmp_path, "Pkg::test_a", flakiness=0.05)
        # 10 runs: alternating pass/fail → ~0.8 flakiness_rate
        for i in range(10):
            import xml.etree.ElementTree as ET
            suite = ET.Element("testsuite")
            suite.set("name", "S")
            tc = ET.SubElement(suite, "testcase")
            tc.set("name", "test_a")
            tc.set("classname", "Pkg")
            if i % 2 == 1:  # odd runs fail
                fl = ET.SubElement(tc, "failure")
                fl.set("message", "err")
            (xml_dir / f"run-{i:03d}.xml").write_text(ET.tostring(suite, encoding="unicode"))
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(input_p), "--history-dir", str(xml_dir)])
        assert result.exit_code == 0
        assert "retire" in result.output.lower() or "Retire" in result.output

    # --- --history-file (CSV) ---

    def test_history_file_csv_exits_0(self, tmp_path):
        input_p = self._minimal_input(tmp_path, "T-001", flakiness=0.1)
        csv_p = tmp_path / "history.csv"
        csv_p.write_text("test_id,flakiness_rate,failure_count_last_30d,total_runs\nT-001,0.1,1,10\n")
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(input_p), "--history-file", str(csv_p)])
        assert result.exit_code == 0

    def test_history_file_json_exits_0(self, tmp_path):
        import json
        input_p = self._minimal_input(tmp_path, "T-001", flakiness=0.1)
        json_p = tmp_path / "history.json"
        json_p.write_text(json.dumps([
            {"test_id": "T-001", "flakiness_rate": 0.1, "failure_count_last_30d": 1, "total_runs": 10}
        ]))
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(input_p), "--history-file", str(json_p)])
        assert result.exit_code == 0

    def test_history_file_missing_exits_2(self, tmp_path):
        input_p = self._minimal_input(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(input_p), "--history-file", str(tmp_path / "no.csv")])
        assert result.exit_code == 2

    def test_history_file_invalid_extension_exits_2(self, tmp_path):
        input_p = self._minimal_input(tmp_path)
        bad = tmp_path / "history.txt"
        bad.write_text("some data")
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(input_p), "--history-file", str(bad)])
        assert result.exit_code == 2

    def test_history_file_overlays_high_flakiness(self, tmp_path):
        """CSV with flakiness_rate above retire threshold pushes test to retire."""
        import yaml
        data = {
            "sprint_context": {
                "stories": [{"id": "S-1", "risk": "low", "changed_areas": ["area-a"]}],
            },
            "test_suite": [
                {
                    "id": "T-001",
                    "name": "Flaky test",
                    "layer": "unit",
                    "coverage_areas": ["area-a"],
                    "execution_time_secs": 5,
                    "flakiness_rate": 0.05,   # below threshold in YAML
                    "automated": True,
                }
            ],
            "constraints": {"flakiness_retire_threshold": 0.30, "time_budget_mins": 60},
        }
        input_p = tmp_path / "input.yaml"
        input_p.write_text(yaml.safe_dump(data))
        csv_p = tmp_path / "history.csv"
        csv_p.write_text(
            "test_id,flakiness_rate,failure_count_last_30d,total_runs\n"
            "T-001,0.95,19,20\n"
        )
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(input_p), "--history-file", str(csv_p)])
        assert result.exit_code == 0
        assert "retire" in result.output.lower() or "Retire" in result.output

    # --- mutual exclusion ---

    def test_cannot_combine_history_dir_and_history_file(self, tmp_path):
        input_p = self._minimal_input(tmp_path)
        xml_dir = tmp_path / "xml"
        xml_dir.mkdir()
        csv_p = tmp_path / "history.csv"
        csv_p.write_text("test_id,flakiness_rate,failure_count_last_30d,total_runs\n")
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["run", str(input_p), "--history-dir", str(xml_dir), "--history-file", str(csv_p)]
        )
        assert result.exit_code == 2

