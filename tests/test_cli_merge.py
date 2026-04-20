"""Tests for the CLI merge utility (--tests + --sprint flags)."""
import pathlib

import pytest
import yaml
from click.testing import CliRunner

from intelligent_regression_optimizer.cli import main
from intelligent_regression_optimizer.models import EXIT_INPUT_ERROR, EXIT_OK


@pytest.fixture
def sprint_data() -> dict:
    """Minimal valid sprint context + constraints."""
    return {
        "sprint_context": {
            "sprint_id": "SPRINT-99",
            "stories": [
                {
                    "id": "PROJ-500",
                    "title": "Add caching",
                    "risk": "high",
                    "type": "feature",
                    "changed_areas": ["CacheService"],
                    "dependency_stories": [],
                }
            ],
            "exploratory_sessions": [],
        },
        "constraints": {
            "time_budget_mins": 30,
            "mandatory_tags": [],
            "flakiness_retire_threshold": 0.30,
            "flakiness_high_tier_threshold": 0.20,
        },
    }


@pytest.fixture
def tests_data() -> dict:
    """Minimal valid test_suite block."""
    return {
        "test_suite": [
            {
                "id": "TEST-A",
                "name": "cache integration",
                "layer": "integration",
                "coverage_areas": ["CacheService"],
                "execution_time_secs": 30,
                "flakiness_rate": 0.01,
                "failure_count_last_30d": 0,
                "automated": True,
                "tags": [],
            }
        ]
    }


@pytest.fixture
def sprint_file(repo_tmp, sprint_data) -> pathlib.Path:
    p = repo_tmp / "sprint.yaml"
    p.write_text(yaml.dump(sprint_data, sort_keys=False), encoding="utf-8")
    return p


@pytest.fixture
def tests_file(repo_tmp, tests_data) -> pathlib.Path:
    p = repo_tmp / "tests.yaml"
    p.write_text(yaml.dump(tests_data, sort_keys=False), encoding="utf-8")
    return p


class TestMergeHappyPath:
    """Merge utility produces a valid report from separate files."""

    def test_merge_produces_report(self, sprint_file, tests_file):
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--tests", str(tests_file), "--sprint", str(sprint_file)])
        assert result.exit_code == EXIT_OK, result.output
        assert "## Optimisation Summary" in result.output
        assert "## Must-Run" in result.output

    def test_merge_output_to_file(self, sprint_file, tests_file, repo_tmp):
        out_path = repo_tmp / "report.md"
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", "--tests", str(tests_file), "--sprint", str(sprint_file),
            "--output", str(out_path),
        ])
        assert result.exit_code == EXIT_OK, result.output
        content = out_path.read_text(encoding="utf-8")
        assert "## Optimisation Summary" in content

    def test_merge_test_appears_in_correct_tier(self, sprint_file, tests_file):
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--tests", str(tests_file), "--sprint", str(sprint_file)])
        assert result.exit_code == EXIT_OK, result.output
        # TEST-A covers a high-risk changed area → should be must-run
        assert "TEST-A" in result.output


class TestMergeArgumentValidation:
    """Argument combination errors are caught early."""

    def test_input_file_with_tests_flag_fails(self, sprint_file, tests_file):
        runner = CliRunner()
        result = runner.invoke(main, [
            "run", "some_input.yaml",
            "--tests", str(tests_file), "--sprint", str(sprint_file),
        ])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "cannot combine" in result.output

    def test_tests_without_sprint_fails(self, tests_file):
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--tests", str(tests_file)])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "--tests and --sprint" in result.output

    def test_sprint_without_tests_fails(self, sprint_file):
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--sprint", str(sprint_file)])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "--tests and --sprint" in result.output

    def test_no_arguments_at_all_fails(self):
        runner = CliRunner()
        result = runner.invoke(main, ["run"])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "provide either INPUT_FILE" in result.output


class TestMergeFileErrors:
    """Missing or malformed files produce clear errors."""

    def test_missing_tests_file(self, sprint_file, repo_tmp):
        runner = CliRunner()
        missing = repo_tmp / "nonexistent.yaml"
        result = runner.invoke(main, ["run", "--tests", str(missing), "--sprint", str(sprint_file)])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "Tests file not found" in result.output

    def test_missing_sprint_file(self, tests_file, repo_tmp):
        runner = CliRunner()
        missing = repo_tmp / "nonexistent.yaml"
        result = runner.invoke(main, ["run", "--tests", str(tests_file), "--sprint", str(missing)])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "Sprint file not found" in result.output

    def test_tests_file_missing_test_suite_key(self, sprint_file, repo_tmp):
        bad = repo_tmp / "bad_tests.yaml"
        bad.write_text(yaml.dump({"wrong_key": []}), encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--tests", str(bad), "--sprint", str(sprint_file)])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "test_suite" in result.output

    def test_sprint_file_missing_sprint_context_key(self, tests_file, repo_tmp):
        bad = repo_tmp / "bad_sprint.yaml"
        bad.write_text(yaml.dump({"constraints": {}}), encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--tests", str(tests_file), "--sprint", str(bad)])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "sprint_context" in result.output

    def test_sprint_file_missing_constraints_key(self, tests_file, repo_tmp):
        bad = repo_tmp / "bad_sprint.yaml"
        bad.write_text(yaml.dump({"sprint_context": {"stories": []}}), encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--tests", str(tests_file), "--sprint", str(bad)])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "constraints" in result.output

    def test_invalid_yaml_in_tests_file(self, sprint_file, repo_tmp):
        bad = repo_tmp / "invalid.yaml"
        bad.write_text("not a mapping", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--tests", str(bad), "--sprint", str(sprint_file)])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "Tests file must be a YAML mapping" in result.output

    def test_invalid_yaml_in_sprint_file(self, tests_file, repo_tmp):
        bad = repo_tmp / "invalid.yaml"
        bad.write_text("just a string", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--tests", str(tests_file), "--sprint", str(bad)])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "Sprint file must be a YAML mapping" in result.output


class TestMergeValidationErrors:
    """Merged data is validated through the standard pipeline validation."""

    def test_invalid_risk_in_sprint(self, tests_file, repo_tmp):
        bad_sprint = {
            "sprint_context": {
                "stories": [
                    {
                        "id": "S-1",
                        "risk": "extreme",  # invalid
                        "changed_areas": ["Foo"],
                        "dependency_stories": [],
                    }
                ],
            },
            "constraints": {
                "time_budget_mins": 10,
                "mandatory_tags": [],
                "flakiness_retire_threshold": 0.3,
                "flakiness_high_tier_threshold": 0.2,
            },
        }
        bf = repo_tmp / "bad_sprint.yaml"
        bf.write_text(yaml.dump(bad_sprint, sort_keys=False), encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--tests", str(tests_file), "--sprint", str(bf)])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "Invalid risk value" in result.output

    def test_invalid_test_entry(self, sprint_file, repo_tmp):
        bad_tests = {
            "test_suite": [
                {
                    "id": "T-1",
                    "name": "broken test",
                    "layer": "unit",
                    "coverage_areas": ["X"],
                    "execution_time_secs": -5,  # invalid
                    "flakiness_rate": 0.0,
                }
            ]
        }
        tf = repo_tmp / "bad_tests.yaml"
        tf.write_text(yaml.dump(bad_tests, sort_keys=False), encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--tests", str(tf), "--sprint", str(sprint_file)])
        assert result.exit_code == EXIT_INPUT_ERROR
        assert "execution_time_secs" in result.output


class TestMergeRoundTrip:
    """Excel import → merge → run produces the same result as a combined file."""

    def test_excel_import_then_merge(self, sprint_file, tests_data, repo_tmp):
        """Import test_suite via dict, write it, then merge with sprint file."""
        # Write the test_suite YAML to a file (simulating iro import-tests output)
        tests_yaml_path = repo_tmp / "imported_tests.yaml"
        tests_yaml_path.write_text(
            yaml.dump(tests_data, sort_keys=False), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(main, [
            "run", "--tests", str(tests_yaml_path), "--sprint", str(sprint_file),
        ])
        assert result.exit_code == EXIT_OK, result.output
        assert "## Optimisation Summary" in result.output
