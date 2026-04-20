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
