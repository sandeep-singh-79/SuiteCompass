"""Template loader for LLM prompt files."""
from __future__ import annotations

from pathlib import Path

_DEFAULT_PROMPT_DIR = Path(__file__).parent / "prompts"


def load_template(
    name: str,
    version: str = "v1",
    prompt_dir: Path | None = None,
) -> str:
    """Load prompts/{version}/{name}.txt and return its content.

    Args:
        name: Template name (without .txt extension).
        version: Subdirectory version, default "v1".
        prompt_dir: Override the prompts root directory. Defaults to the
            package-bundled prompts/ folder.

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    base = prompt_dir if prompt_dir is not None else _DEFAULT_PROMPT_DIR
    path = base / version / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")
