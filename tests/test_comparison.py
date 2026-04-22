"""Tests for comparison reporter."""
from __future__ import annotations

from intelligent_regression_optimizer.llm_client import FakeLLMClient
from intelligent_regression_optimizer.models import EXIT_OK, FlowResult, ScoredTest, TierResult
from intelligent_regression_optimizer.llm_flow import LLMFlowResult
from intelligent_regression_optimizer.comparison import build_comparison_report


def _make_llm_flow_result(mode: str = "llm", repair_actions: list[str] | None = None) -> LLMFlowResult:
    return LLMFlowResult(
        flow_result=FlowResult(exit_code=EXIT_OK, message="LLM output here", output_path=None),
        recommendation_mode=mode,
        raw_llm_output="raw LLM text",
        repair_actions=repair_actions or [],
    )


_DETERMINISTIC_REPORT = "## Optimisation Summary\n\nRecommendation Mode: deterministic\n"


def test_build_comparison_report_returns_string():
    result = build_comparison_report(_DETERMINISTIC_REPORT, _make_llm_flow_result())
    assert isinstance(result, str) and len(result) > 0


def test_contains_comparison_summary_section():
    result = build_comparison_report(_DETERMINISTIC_REPORT, _make_llm_flow_result())
    assert "## Comparison Summary" in result


def test_contains_deterministic_output_section():
    result = build_comparison_report(_DETERMINISTIC_REPORT, _make_llm_flow_result())
    assert "## Deterministic Output" in result
    assert _DETERMINISTIC_REPORT in result


def test_contains_llm_output_section():
    result = build_comparison_report(_DETERMINISTIC_REPORT, _make_llm_flow_result())
    assert "## LLM Output" in result
    assert "LLM output here" in result


def test_comparison_summary_contains_mode():
    result = build_comparison_report(_DETERMINISTIC_REPORT, _make_llm_flow_result(mode="llm-repaired"))
    assert "llm-repaired" in result


def test_repair_log_present_when_repairs_applied():
    result = build_comparison_report(
        _DETERMINISTIC_REPORT,
        _make_llm_flow_result(repair_actions=["Injected missing label: 'Total Must-Run:'"]),
    )
    assert "## Repair Log" in result
    assert "Total Must-Run" in result


def test_repair_log_absent_when_no_repairs():
    result = build_comparison_report(_DETERMINISTIC_REPORT, _make_llm_flow_result(repair_actions=[]))
    assert "## Repair Log" not in result


def test_comparison_summary_contains_repair_count():
    result = build_comparison_report(
        _DETERMINISTIC_REPORT,
        _make_llm_flow_result(repair_actions=["fix1", "fix2"]),
    )
    assert "2" in result
