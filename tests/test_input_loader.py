"""Unit tests for input_loader.py — written RED before implementation."""
import pathlib
import textwrap

import pytest
import yaml

from intelligent_regression_optimizer.input_loader import (
    InputValidationError,
    load_input,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
VALID_YAML = FIXTURES / "valid_input.yaml"
TMP = pathlib.Path(__file__).parent.parent / "tmp"


def _write_tmp(name: str, content: str) -> pathlib.Path:
    TMP.mkdir(exist_ok=True)
    p = TMP / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestValidInput:
    def test_valid_yaml_loads_successfully(self):
        pkg = load_input(str(VALID_YAML))
        assert pkg.raw is not None
        assert pkg.normalized is not None

    def test_source_path_recorded(self):
        pkg = load_input(str(VALID_YAML))
        assert pkg.source_path == str(VALID_YAML)

    def test_stories_present(self):
        pkg = load_input(str(VALID_YAML))
        stories = pkg.normalized["sprint_context"]["stories"]
        assert len(stories) >= 1

    def test_test_suite_present(self):
        pkg = load_input(str(VALID_YAML))
        assert len(pkg.normalized["test_suite"]) >= 1

    def test_constraints_present(self):
        pkg = load_input(str(VALID_YAML))
        assert "constraints" in pkg.normalized

    def test_dependency_story_resolved(self):
        pkg = load_input(str(VALID_YAML))
        # Story PROJ-1100 depends on PROJ-1099; resolved deps should be present under resolved_deps
        stories = {s["id"]: s for s in pkg.normalized["sprint_context"]["stories"]}
        assert "resolved_deps" in stories["PROJ-1100"]
        dep_ids = [s["id"] for s in stories["PROJ-1100"]["resolved_deps"]]
        assert "PROJ-1099" in dep_ids


# ---------------------------------------------------------------------------
# Missing required top-level keys
# ---------------------------------------------------------------------------

class TestMissingTopLevelKeys:
    def test_missing_sprint_context_raises(self):
        p = _write_tmp("no_sprint.yaml", """\
            test_suite: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="sprint_context"):
            load_input(str(p))

    def test_missing_test_suite_raises(self):
        p = _write_tmp("no_tests.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="test_suite"):
            load_input(str(p))

    def test_missing_constraints_raises(self):
        p = _write_tmp("no_constraints.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            test_suite: []
        """)
        with pytest.raises(InputValidationError, match="constraints"):
            load_input(str(p))


# ---------------------------------------------------------------------------
# Story validation
# ---------------------------------------------------------------------------

class TestStoryValidation:
    def test_story_missing_id_raises(self):
        p = _write_tmp("story_no_id.yaml", """\
            sprint_context:
              sprint_id: S1
              stories:
                - risk: high
                  changed_areas: [Foo]
                  dependency_stories: []
              exploratory_sessions: []
            test_suite: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="id"):
            load_input(str(p))

    def test_story_missing_risk_raises(self):
        p = _write_tmp("story_no_risk.yaml", """\
            sprint_context:
              sprint_id: S1
              stories:
                - id: S-1
                  changed_areas: [Foo]
                  dependency_stories: []
              exploratory_sessions: []
            test_suite: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="risk"):
            load_input(str(p))

    def test_story_invalid_risk_value_raises(self):
        p = _write_tmp("story_bad_risk.yaml", """\
            sprint_context:
              sprint_id: S1
              stories:
                - id: S-1
                  risk: critical
                  changed_areas: [Foo]
                  dependency_stories: []
              exploratory_sessions: []
            test_suite: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="risk"):
            load_input(str(p))


# ---------------------------------------------------------------------------
# Test record validation
# ---------------------------------------------------------------------------

class TestTestRecordValidation:
    def test_test_missing_id_raises(self):
        p = _write_tmp("test_no_id.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            test_suite:
              - name: foo
                layer: unit
                coverage_areas: [Foo]
                execution_time_secs: 10
                flakiness_rate: 0.0
                failure_count_last_30d: 0
                automated: true
                tags: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="id"):
            load_input(str(p))

    def test_test_missing_layer_raises(self):
        p = _write_tmp("test_no_layer.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            test_suite:
              - id: T-1
                name: foo
                coverage_areas: [Foo]
                execution_time_secs: 10
                flakiness_rate: 0.0
                failure_count_last_30d: 0
                automated: true
                tags: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="layer"):
            load_input(str(p))

    def test_test_missing_coverage_areas_raises(self):
        p = _write_tmp("test_no_coverage.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            test_suite:
              - id: T-1
                name: foo
                layer: unit
                execution_time_secs: 10
                flakiness_rate: 0.0
                failure_count_last_30d: 0
                automated: true
                tags: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="coverage_areas"):
            load_input(str(p))

    def test_negative_execution_time_raises(self):
        p = _write_tmp("test_neg_time.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            test_suite:
              - id: T-1
                name: foo
                layer: unit
                coverage_areas: [Foo]
                execution_time_secs: -5
                flakiness_rate: 0.0
                failure_count_last_30d: 0
                automated: true
                tags: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="execution_time_secs"):
            load_input(str(p))

    def test_flakiness_above_1_raises(self):
        p = _write_tmp("test_flak_high.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            test_suite:
              - id: T-1
                name: foo
                layer: unit
                coverage_areas: [Foo]
                execution_time_secs: 10
                flakiness_rate: 1.5
                failure_count_last_30d: 0
                automated: true
                tags: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="flakiness_rate"):
            load_input(str(p))

    def test_flakiness_below_0_raises(self):
        p = _write_tmp("test_flak_neg.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            test_suite:
              - id: T-1
                name: foo
                layer: unit
                coverage_areas: [Foo]
                execution_time_secs: 10
                flakiness_rate: -0.1
                failure_count_last_30d: 0
                automated: true
                tags: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="flakiness_rate"):
            load_input(str(p))


# ---------------------------------------------------------------------------
# File-level errors
# ---------------------------------------------------------------------------

class TestFileErrors:
    def test_nonexistent_file_raises(self):
        with pytest.raises((InputValidationError, FileNotFoundError)):
            load_input("/nonexistent/path/input.yaml")

    def test_missing_dependency_story_raises(self):
        p = _write_tmp("missing_dep.yaml", """\
            sprint_context:
              sprint_id: S1
              stories:
                - id: S-1
                  risk: high
                  changed_areas: [Foo]
                  dependency_stories:
                    - S-NONEXISTENT
              exploratory_sessions: []
            test_suite: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="S-NONEXISTENT"):
            load_input(str(p))


# ---------------------------------------------------------------------------
# Type validation — collection types must be lists (Critical fix #3)
# ---------------------------------------------------------------------------

class TestCollectionTypeValidation:
    """tests must be a list, stories must be a list, mandatory_tags must be a list."""

    def test_test_suite_as_dict_raises(self):
        p = _write_tmp("test_suite_dict.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            test_suite: {}
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="test_suite must be a list"):
            load_input(str(p))

    def test_test_suite_as_string_raises(self):
        p = _write_tmp("test_suite_str.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            test_suite: not_a_list
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="test_suite must be a list"):
            load_input(str(p))

    def test_stories_as_dict_raises(self):
        p = _write_tmp("stories_dict.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: {}
              exploratory_sessions: []
            test_suite: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="stories must be a list"):
            load_input(str(p))

    def test_mandatory_tags_as_string_raises(self):
        p = _write_tmp("mandatory_tags_str.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            test_suite: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: critical
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="mandatory_tags must be a list"):
            load_input(str(p))

    def test_dependency_stories_as_string_raises(self):
        p = _write_tmp("dep_stories_str.yaml", """\
            sprint_context:
              sprint_id: S1
              stories:
                - id: S-1
                  risk: high
                  changed_areas: [Foo]
                  dependency_stories: S-2
              exploratory_sessions: []
            test_suite: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="dependency_stories must be a list"):
            load_input(str(p))


# ---------------------------------------------------------------------------
# Required field: name (Critical fix #2)
# ---------------------------------------------------------------------------

class TestMissingNameField:
    def test_test_missing_name_raises(self):
        p = _write_tmp("no_name.yaml", """\
            sprint_context:
              sprint_id: S1
              stories: []
              exploratory_sessions: []
            test_suite:
              - id: T1
                layer: unit
                coverage_areas: [Foo]
                execution_time_secs: 10
                flakiness_rate: 0.01
                automated: true
                tags: []
            constraints:
              time_budget_mins: 30
              mandatory_tags: []
              flakiness_retire_threshold: 0.3
              flakiness_high_tier_threshold: 0.2
        """)
        with pytest.raises(InputValidationError, match="name"):
            load_input(str(p))
