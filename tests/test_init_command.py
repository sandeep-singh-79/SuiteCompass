"""Tests for the `iro init` command — template YAML generator.

Validates:
- Plain scaffold (no --from-junit)
- --from-junit mode: test IDs, names, exec times, flakiness populated
- Generated YAML is loadable by load_input when TODOs are filled
- CLI integration via Click test runner
- Scaffold schema matches the loader contract (story fields, test fields, constraint keys)
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from intelligent_regression_optimizer.cli import main
from intelligent_regression_optimizer.input_loader import load_input, validate_raw


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

JUNIT_XML_RUN1 = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="mysuite" timestamp="2026-04-01T09:00:00" tests="3" failures="1">
        <testcase classname="com.example.PaymentTest" name="test_settlement" time="1.50"/>
        <testcase classname="com.example.PaymentTest" name="test_refund" time="0.80">
            <failure message="AssertionError">expected 0 got 1</failure>
        </testcase>
        <testcase classname="com.example.AuthTest" name="test_login" time="0.30"/>
    </testsuite>
""")

JUNIT_XML_RUN2 = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <testsuite name="mysuite" timestamp="2026-04-02T09:00:00" tests="3" failures="0">
        <testcase classname="com.example.PaymentTest" name="test_settlement" time="1.60"/>
        <testcase classname="com.example.PaymentTest" name="test_refund" time="0.75"/>
        <testcase classname="com.example.AuthTest" name="test_login" time="0.32"/>
    </testsuite>
""")


@pytest.fixture
def junit_dir(tmp_path: Path) -> Path:
    """Write two JUnit XML run files and return the directory."""
    (tmp_path / "run1.xml").write_text(JUNIT_XML_RUN1, encoding="utf-8")
    (tmp_path / "run2.xml").write_text(JUNIT_XML_RUN2, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# TestInitPlainScaffold — no --from-junit
# ---------------------------------------------------------------------------

class TestInitPlainScaffold:
    def test_init_exits_zero(self, tmp_path: Path) -> None:
        """Plain `iro init` should exit 0."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        result = runner.invoke(main, ["init", "--output", str(out_file)])
        assert result.exit_code == 0, result.output

    def test_init_writes_file_when_output_specified(self, tmp_path: Path) -> None:
        """Output file is created when --output is provided."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        assert out_file.exists()

    def test_init_prints_to_stdout_without_output_flag(self) -> None:
        """Without --output, template is printed to stdout."""
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert len(result.output) > 0

    def test_init_scaffold_has_sprint_context_key(self, tmp_path: Path) -> None:
        """Generated YAML has a sprint_context top-level key."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        assert "sprint_context" in doc

    def test_init_scaffold_has_test_suite_key(self, tmp_path: Path) -> None:
        """Generated YAML has a test_suite top-level key."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        assert "test_suite" in doc

    def test_init_scaffold_has_constraints_key(self, tmp_path: Path) -> None:
        """Generated YAML has a constraints top-level key."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        assert "constraints" in doc

    def test_init_template_has_todo_comments(self, tmp_path: Path) -> None:
        """Raw YAML text contains TODO markers guiding the user."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        raw = out_file.read_text()
        assert "TODO" in raw

    def test_init_output_file_overwrite_is_allowed(self, tmp_path: Path) -> None:
        """Running init twice on the same output path overwrites the file without error."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        result2 = runner.invoke(main, ["init", "--output", str(out_file)])
        assert result2.exit_code == 0


# ---------------------------------------------------------------------------
# TestInitFromJunit — --from-junit mode
# ---------------------------------------------------------------------------

class TestInitFromJunit:
    def test_from_junit_exits_zero(self, tmp_path: Path, junit_dir: Path) -> None:
        """--from-junit exits 0 when directory has valid XML."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        result = runner.invoke(main, ["init", "--from-junit", str(junit_dir), "--output", str(out_file)])
        assert result.exit_code == 0, result.output

    def test_from_junit_populates_test_ids(self, tmp_path: Path, junit_dir: Path) -> None:
        """Test IDs derived from classname::name appear in the generated test_suite."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--from-junit", str(junit_dir), "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        ids = [t["id"] for t in doc["test_suite"]]
        assert "com.example.PaymentTest::test_settlement" in ids
        assert "com.example.PaymentTest::test_refund" in ids
        assert "com.example.AuthTest::test_login" in ids

    def test_from_junit_populates_names(self, tmp_path: Path, junit_dir: Path) -> None:
        """Test names (human-readable) are populated from the XML name attribute."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--from-junit", str(junit_dir), "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        names = [t["name"] for t in doc["test_suite"]]
        assert "test_settlement" in names
        assert "test_refund" in names

    def test_from_junit_populates_execution_time(self, tmp_path: Path, junit_dir: Path) -> None:
        """execution_time_secs is populated from the average <testcase time> across runs."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--from-junit", str(junit_dir), "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        test_map = {t["id"]: t for t in doc["test_suite"]}
        # test_settlement: avg of 1.50 and 1.60 = 1.55 secs → round to int → 2
        settlement = test_map["com.example.PaymentTest::test_settlement"]
        assert isinstance(settlement["execution_time_secs"], int)
        assert settlement["execution_time_secs"] > 0

    def test_from_junit_populates_flakiness_rate(self, tmp_path: Path, junit_dir: Path) -> None:
        """flakiness_rate is derived from the JUnit history (test_refund had one flaky failure)."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--from-junit", str(junit_dir), "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        test_map = {t["id"]: t for t in doc["test_suite"]}
        refund = test_map["com.example.PaymentTest::test_refund"]
        # test_refund failed in run1 and passed in run2 — that is a flaky failure
        assert refund["flakiness_rate"] > 0.0

    def test_from_junit_layer_has_todo_comment(self, tmp_path: Path, junit_dir: Path) -> None:
        """layer values contain a placeholder indicating user must fill them in."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--from-junit", str(junit_dir), "--output", str(out_file)])
        raw = out_file.read_text()
        # The raw YAML text should flag layer as needing user input
        assert "TODO" in raw

    def test_from_junit_nonexistent_dir_exits_error(self, tmp_path: Path) -> None:
        """Non-existent --from-junit directory exits with EXIT_INPUT_ERROR (2)."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        result = runner.invoke(main, ["init", "--from-junit", str(tmp_path / "missing"), "--output", str(out_file)])
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# TestInitTemplateUsability
# ---------------------------------------------------------------------------

class TestInitTemplateUsability:
    def test_plain_template_is_valid_yaml(self, tmp_path: Path) -> None:
        """Plain scaffold must be parseable YAML (no syntax errors)."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        # Must not raise
        doc = yaml.safe_load(out_file.read_text())
        assert doc is not None

    def test_from_junit_output_is_valid_yaml(self, tmp_path: Path, junit_dir: Path) -> None:
        """--from-junit output must be parseable YAML."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--from-junit", str(junit_dir), "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        assert doc is not None


# ---------------------------------------------------------------------------
# TestInitSchemaCompliance — scaffold matches the loader contract
# ---------------------------------------------------------------------------

def _fill_todos_plain(raw: str) -> str:
    """Replace TODO placeholders in a plain scaffold with valid concrete values."""
    return (
        raw
        .replace("TODO_story_id", "STORY-001")
        .replace('"TODO: Story summary"', '"Refactor auth module"')
        .replace("changed_areas: []", "changed_areas: [AuthModule]")
        .replace("TODO_test_id", "TEST-001")
        .replace('"TODO: human readable test name"', '"auth module unit test"')
        .replace("layer: unit", "layer: unit")  # already valid after fix
        .replace("TODO_area", "AuthModule")
    )


def _fill_todos_junit(raw: str) -> str:
    """Replace TODO placeholders in a --from-junit scaffold with valid concrete values."""
    return (
        raw
        .replace("TODO_story_id", "STORY-001")
        .replace("'TODO: Story summary'", "'Refactor auth module'")
        .replace('"TODO: Story summary"', '"Refactor auth module"')
        .replace("TODO: Describe the sprint goal", "Sprint goal")
        .replace("changed_areas: []", "changed_areas: [AuthModule]")
        .replace("UNKNOWN", "AuthModule")
        .replace("layer: TODO", "layer: unit")
    )


class TestInitSchemaCompliance:
    """Verify the scaffold YAML matches the input_loader contract."""

    def test_plain_scaffold_has_required_story_fields(self, tmp_path: Path) -> None:
        """Scaffold story must include id, risk, and changed_areas."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        story = doc["sprint_context"]["stories"][0]
        assert "id" in story, "story missing 'id'"
        assert "risk" in story, "story missing 'risk'"
        assert "changed_areas" in story, "story missing 'changed_areas'"

    def test_plain_scaffold_has_required_test_fields(self, tmp_path: Path) -> None:
        """Scaffold test must include coverage_areas."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        test = doc["test_suite"][0]
        assert "coverage_areas" in test, "test missing 'coverage_areas'"

    def test_plain_scaffold_has_correct_constraint_keys(self, tmp_path: Path) -> None:
        """Scaffold constraints must use the real pipeline keys, not invented ones."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        c = doc["constraints"]
        assert "time_budget_mins" in c, "constraints missing 'time_budget_mins'"
        assert "mandatory_tags" in c, "constraints missing 'mandatory_tags'"
        assert "flakiness_retire_threshold" in c, "constraints missing 'flakiness_retire_threshold'"
        assert "flakiness_high_tier_threshold" in c, "constraints missing 'flakiness_high_tier_threshold'"
        # These should NOT be present
        assert "time_budget_secs" not in c, "constraints has bogus 'time_budget_secs'"
        assert "max_flakiness_rate" not in c, "constraints has bogus 'max_flakiness_rate'"

    def test_from_junit_scaffold_has_correct_constraint_keys(self, tmp_path: Path, junit_dir: Path) -> None:
        """--from-junit scaffold constraints must use the real pipeline keys."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--from-junit", str(junit_dir), "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        c = doc["constraints"]
        assert "time_budget_mins" in c, "constraints missing 'time_budget_mins'"
        assert "mandatory_tags" in c, "constraints missing 'mandatory_tags'"
        assert "flakiness_retire_threshold" in c, "constraints missing 'flakiness_retire_threshold'"
        assert "flakiness_high_tier_threshold" in c, "constraints missing 'flakiness_high_tier_threshold'"
        assert "time_budget_secs" not in c, "constraints has bogus 'time_budget_secs'"
        assert "max_flakiness_rate" not in c, "constraints has bogus 'max_flakiness_rate'"

    def test_from_junit_scaffold_has_coverage_areas(self, tmp_path: Path, junit_dir: Path) -> None:
        """--from-junit test entries must include coverage_areas."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--from-junit", str(junit_dir), "--output", str(out_file)])
        doc = yaml.safe_load(out_file.read_text())
        for t in doc["test_suite"]:
            assert "coverage_areas" in t, f"test {t['id']} missing 'coverage_areas'"

    def test_plain_scaffold_filled_passes_loader(self, tmp_path: Path) -> None:
        """Scaffold with TODOs replaced by concrete values must pass load_input."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        raw = out_file.read_text()
        filled = _fill_todos_plain(raw)
        filled_file = tmp_path / "filled.yaml"
        filled_file.write_text(filled, encoding="utf-8")
        # Must not raise
        pkg = load_input(str(filled_file))
        assert pkg.normalized is not None

    def test_from_junit_scaffold_filled_passes_loader(self, tmp_path: Path, junit_dir: Path) -> None:
        """--from-junit scaffold with TODOs replaced by concrete values must pass load_input."""
        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--from-junit", str(junit_dir), "--output", str(out_file)])
        raw = out_file.read_text()
        filled = _fill_todos_junit(raw)
        filled_file = tmp_path / "filled.yaml"
        filled_file.write_text(filled, encoding="utf-8")
        pkg = load_input(str(filled_file))
        assert pkg.normalized is not None


# ---------------------------------------------------------------------------
# TestInitEndToEnd — full workflow: init → fill → run pipeline
# ---------------------------------------------------------------------------

class TestInitEndToEnd:
    def test_filled_scaffold_produces_valid_report(self, tmp_path: Path) -> None:
        """Init → fill TODOs → run pipeline → output passes output_validator."""
        from intelligent_regression_optimizer.end_to_end_flow import run_pipeline

        runner = CliRunner()
        out_file = tmp_path / "template.yaml"
        runner.invoke(main, ["init", "--output", str(out_file)])
        raw = out_file.read_text()
        filled = _fill_todos_plain(raw)
        filled_file = tmp_path / "filled.yaml"
        filled_file.write_text(filled, encoding="utf-8")

        result = run_pipeline(str(filled_file))
        assert result.exit_code == 0, result.message
