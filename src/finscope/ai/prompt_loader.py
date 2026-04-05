"""Prompt loader for AI agents.

Loads system prompts from ``.md`` files in the ``prompts/`` directory.
Prompts live as plain text files so they can be iterated without touching
Python code.

Override mechanism:
    Set ``FINSCOPE_PROMPTS_DIR`` to a directory containing your own prompt
    files.  Any file found there takes priority over the built-in defaults.

    export FINSCOPE_PROMPTS_DIR=~/my-prompts
    # ~/my-prompts/analyst.md will override the built-in analyst prompt
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

__all__ = ["load_prompt"]

_BUILTIN_DIR = Path(__file__).parent / "prompts"


@lru_cache(maxsize=16)
def load_prompt(name: str) -> str:
    """Load a system prompt by name.

    Resolution order:
        1. ``$FINSCOPE_PROMPTS_DIR/<name>.md`` (user override)
        2. Built-in ``prompts/<name>.md``

    Args:
        name: Prompt name without extension (e.g. ``"analyst"``, ``"qa"``).

    Returns:
        The prompt text with leading/trailing whitespace stripped.

    Raises:
        FileNotFoundError: If the prompt file does not exist in either location.
    """
    # 1. User override directory
    override_dir = os.environ.get("FINSCOPE_PROMPTS_DIR")
    if override_dir:
        override_path = Path(override_dir) / f"{name}.md"
        if override_path.is_file():
            return override_path.read_text(encoding="utf-8").strip()

    # 2. Built-in prompts
    builtin_path = _BUILTIN_DIR / f"{name}.md"
    if builtin_path.is_file():
        return builtin_path.read_text(encoding="utf-8").strip()

    raise FileNotFoundError(
        f"Prompt '{name}' not found. Searched:\n"
        f"  - {override_dir}/{name}.md (override)\n"
        f"  - {builtin_path} (built-in)"
        if override_dir
        else f"Prompt '{name}' not found at {builtin_path}"
    )
