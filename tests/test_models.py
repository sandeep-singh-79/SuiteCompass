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


# ---------------------------------------------------------------------------
# F1.1 RED — flaky-critical fields on ScoredTest and TierResult
# ---------------------------------------------------------------------------

class TestScoredTestFlakyCriticalFields:
    def test_is_flaky_critical_defaults_false(self):
        st = ScoredTest(
            test_id="T1", name="n", raw_score=5.0, tier="should-run",
            is_override=False, override_reason=None, is_manual=False,
        )
        assert st.is_flaky_critical is False

    def test_flaky_critical_reason_defaults_none(self):
        st = ScoredTest(
            test_id="T1", name="n", raw_score=5.0, tier="should-run",
            is_override=False, override_reason=None, is_manual=False,
        )
        assert st.flaky_critical_reason is None

    def test_is_flaky_critical_can_be_set_true(self):
        st = ScoredTest(
            test_id="T1", name="n", raw_score=5.0, tier="flaky-critical",
            is_override=False, override_reason=None, is_manual=False,
            is_flaky_critical=True, flaky_critical_reason="unique:[Checkout]",
        )
        assert st.is_flaky_critical is True
        assert st.flaky_critical_reason == "unique:[Checkout]"

    def test_flaky_critical_tier_string_accepted(self):
        st = ScoredTest(
            test_id="T1", name="n", raw_score=7.0, tier="flaky-critical",
            is_override=False, override_reason=None, is_manual=False,
            is_flaky_critical=True,
        )
        assert st.tier == "flaky-critical"


class TestTierResultFlakyCriticalList:
    def test_flaky_critical_list_defaults_empty(self):
        tr = TierResult()
        assert tr.flaky_critical == []

    def test_flaky_critical_list_accepts_scored_tests(self):
        st = ScoredTest(
            test_id="T1", name="n", raw_score=5.0, tier="flaky-critical",
            is_override=False, override_reason=None, is_manual=False,
            is_flaky_critical=True,
        )
        tr = TierResult(flaky_critical=[st])
        assert len(tr.flaky_critical) == 1
        assert tr.flaky_critical[0].test_id == "T1"

    def test_existing_tier_lists_unaffected(self):
        tr = TierResult(
            must_run=[], should_run=[], defer=[], retire=[],
            budget_overflow=False, flaky_critical=[],
        )
        assert tr.must_run == []
        assert tr.budget_overflow is False
