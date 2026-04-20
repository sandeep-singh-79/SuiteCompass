"""Unit tests for models.py — written RED before implementation."""
import pytest
from intelligent_regression_optimizer.models import (
    InputPackage,
    ScoredTest,
    TierResult,
    ValidationResult,
    FlowResult,
    EXIT_OK,
    EXIT_VALIDATION_ERROR,
    EXIT_INPUT_ERROR,
)


class TestExitCodes:
    def test_exit_ok_is_zero(self):
        assert EXIT_OK == 0

    def test_exit_validation_error_is_one(self):
        assert EXIT_VALIDATION_ERROR == 1

    def test_exit_input_error_is_two(self):
        assert EXIT_INPUT_ERROR == 2

    def test_exit_codes_are_distinct(self):
        assert len({EXIT_OK, EXIT_VALIDATION_ERROR, EXIT_INPUT_ERROR}) == 3


class TestValidationResult:
    def test_is_valid_true_when_no_errors(self):
        vr = ValidationResult(errors=[], total_checks=5)
        assert vr.is_valid is True

    def test_is_valid_false_when_errors_present(self):
        vr = ValidationResult(errors=["missing heading"], total_checks=5)
        assert vr.is_valid is False

    def test_total_checks_stored(self):
        vr = ValidationResult(errors=[], total_checks=13)
        assert vr.total_checks == 13

    def test_errors_list_stored(self):
        errs = ["err1", "err2"]
        vr = ValidationResult(errors=errs, total_checks=2)
        assert vr.errors == errs


class TestScoredTest:
    def test_fields_accessible(self):
        st = ScoredTest(
            test_id="T001",
            name="payment flow test",
            raw_score=9.2,
            tier="must-run",
            is_override=False,
            override_reason=None,
            is_manual=False,
        )
        assert st.test_id == "T001"
        assert st.tier == "must-run"
        assert st.is_override is False
        assert st.is_manual is False


class TestTierResult:
    def test_fields_accessible(self):
        tr = TierResult(
            must_run=[],
            should_run=[],
            defer=[],
            retire=[],
            budget_overflow=False,
        )
        assert tr.budget_overflow is False
        assert tr.must_run == []


class TestFlowResult:
    def test_fields_accessible(self):
        fr = FlowResult(exit_code=EXIT_OK, message="ok", output_path=None)
        assert fr.exit_code == EXIT_OK
        assert fr.output_path is None
