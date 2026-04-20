"""Round-trip integration test: import xlsx -> fill stubs -> iro run -> exit 0. (S6)"""
from __future__ import annotations

import pathlib

import openpyxl
import pytest
import yaml
from click.testing import CliRunner

from intelligent_regression_optimizer.cli import main

TEMPLATES = pathlib.Path(__file__).parent.parent / "templates"
REPO_TMP = pathlib.Path(__file__).parent / ".tmp"


class TestExcelRoundTrip:
    """Import template xlsx, inject sprint_context + constraints, run pipeline."""

    def test_import_then_run_exits_0(self):
        """Full round-trip: template -> YAML -> inject sprint data -> iro run -> exit 0."""
        REPO_TMP.mkdir(parents=True, exist_ok=True)
        runner = CliRunner()

        # Step 1: import the Excel template to YAML
        import_result = runner.invoke(
            main,
            ["import-tests", str(TEMPLATES / "test_suite_template.xlsx"),
             "--output", str(REPO_TMP / "roundtrip_imported.yaml")],
        )
        assert import_result.exit_code == 0, f"import-tests failed: {import_result.output}"

        # Step 2: load the generated YAML and inject a valid sprint_context + constraints
        generated = yaml.safe_load(
            (REPO_TMP / "roundtrip_imported.yaml").read_text(encoding="utf-8")
        )
        generated["sprint_context"] = {
            "sprint_id": "SPRINT-RT-01",
            "stories": [
                {
                    "id": "ST-1",
                    "title": "Payment retry logic",
                    "risk": "high",
                    "type": "feature",
                    "changed_areas": ["PaymentService", "RetryHandler"],
                    "dependency_stories": [],
                }
            ],
            "exploratory_sessions": [],
        }
        generated["constraints"] = {
            "time_budget_mins": 60,
            "mandatory_tags": [],
            "flakiness_retire_threshold": 0.30,
            "flakiness_high_tier_threshold": 0.20,
        }
        combined_path = REPO_TMP / "roundtrip_combined.yaml"
        combined_path.write_text(
            yaml.dump(generated, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

        # Step 3: run the pipeline
        run_result = runner.invoke(main, ["run", str(combined_path)])
        assert run_result.exit_code == 0, f"iro run failed: {run_result.output}"
        assert "## Optimisation Summary" in run_result.output

    def test_imported_yaml_has_correct_test_count(self):
        """Template has 5 rows — imported YAML should have 5 tests."""
        runner = CliRunner()
        result = runner.invoke(main, ["import-tests", str(TEMPLATES / "test_suite_template.xlsx")])
        parsed = yaml.safe_load(result.output)
        assert len(parsed["test_suite"]) == 5

    def test_imported_manual_test_automated_false(self):
        """Template row 5 has automated=false — should survive the round-trip."""
        runner = CliRunner()
        result = runner.invoke(main, ["import-tests", str(TEMPLATES / "test_suite_template.xlsx")])
        parsed = yaml.safe_load(result.output)
        manual = next((t for t in parsed["test_suite"] if t["id"] == "TEST-005"), None)
        assert manual is not None
        assert manual["automated"] is False
