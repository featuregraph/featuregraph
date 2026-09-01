"""Capture the environment a study ran in.

Studies record which software produced their results so a rerun can be
compared against the recorded environment, not just the recorded numbers.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import ModuleType


def git_commit(repo_root: Path | None = None) -> str:
    """Return the current commit hash, raising if the tree is not a git repo."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()


def module_versions(*modules: ModuleType) -> dict[str, str]:
    """Return ``{module_name: module.__version__}`` for already-imported modules.

    Pass the imported modules themselves (``module_versions(np, pd, scipy)``)
    rather than names, since a study runner has already imported whatever it
    depends on.
    """
    return {module.__name__: module.__version__ for module in modules}
