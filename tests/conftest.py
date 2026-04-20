"""Shared pytest fixtures."""
import pathlib
import shutil
import pytest

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
BENCHMARKS_DIR = pathlib.Path(__file__).parent.parent / "benchmarks"
REPO_TMP_DIR = pathlib.Path(__file__).parent / ".tmp"


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    return FIXTURES_DIR


@pytest.fixture
def benchmarks_dir() -> pathlib.Path:
    return BENCHMARKS_DIR


@pytest.fixture
def repo_tmp(request) -> pathlib.Path:
    """Repo-local temp directory under tests/.tmp/.

    Each test gets an isolated subdirectory named after the test node.
    The directory is created before and cleaned after each test.
    """
    safe_name = request.node.name.replace("/", "_").replace("\\", "_")
    d = REPO_TMP_DIR / safe_name
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)
