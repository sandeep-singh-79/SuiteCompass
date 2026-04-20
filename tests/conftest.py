"""Shared pytest fixtures."""
import pathlib
import pytest

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
BENCHMARKS_DIR = pathlib.Path(__file__).parent.parent / "benchmarks"


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    return FIXTURES_DIR


@pytest.fixture
def benchmarks_dir() -> pathlib.Path:
    return BENCHMARKS_DIR
