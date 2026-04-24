"""Tests for public API surface of intelligent_regression_optimizer package.

Verifies:
- All advertised symbols are importable from the package root
- __version__ exists and matches pyproject.toml
- __all__ is defined and matches the exported symbols
"""
from __future__ import annotations

import importlib
import tomllib
from pathlib import Path


def _pyproject_version() -> str:
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


class TestPublicAPIImports:
    def test_run_pipeline_importable(self):
        from intelligent_regression_optimizer import run_pipeline  # noqa: F401
        assert callable(run_pipeline)

    def test_run_pipeline_from_merged_importable(self):
        from intelligent_regression_optimizer import run_pipeline_from_merged  # noqa: F401
        assert callable(run_pipeline_from_merged)

    def test_score_tests_importable(self):
        from intelligent_regression_optimizer import score_tests  # noqa: F401
        assert callable(score_tests)

    def test_validate_output_importable(self):
        from intelligent_regression_optimizer import validate_output  # noqa: F401
        assert callable(validate_output)

    def test_load_input_importable(self):
        from intelligent_regression_optimizer import load_input  # noqa: F401
        assert callable(load_input)


class TestVersionMetadata:
    def test_version_attribute_exists(self):
        import intelligent_regression_optimizer as pkg
        assert hasattr(pkg, "__version__")

    def test_version_matches_pyproject(self):
        import intelligent_regression_optimizer as pkg
        assert pkg.__version__ == _pyproject_version()

    def test_version_is_string(self):
        import intelligent_regression_optimizer as pkg
        assert isinstance(pkg.__version__, str)


class TestDunderAll:
    def test_all_defined(self):
        import intelligent_regression_optimizer as pkg
        assert hasattr(pkg, "__all__")

    def test_all_is_list_or_tuple(self):
        import intelligent_regression_optimizer as pkg
        assert isinstance(pkg.__all__, (list, tuple))

    def test_all_symbols_importable(self):
        import intelligent_regression_optimizer as pkg
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"__all__ lists {name!r} but it is not importable"
