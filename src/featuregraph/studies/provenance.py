"""Capture the environment a study ran in.

Studies record which software produced their results so a rerun can be
compared against the recorded environment, not just the recorded numbers.
"""

from __future__ import annotations

import subprocess
from importlib.metadata import version as _distribution_version
from pathlib import Path
from types import ModuleType


def git_commit(repo_root: Path | None = None) -> str:
    """Return the current commit hash, raising if the tree is not a git repo."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()


def git_commit_or_none(repo_root: Path | None = None) -> str | None:
    """Return the current commit hash, or None outside a git repository.

    Use this in a report where a missing commit hash is worth recording as
    absent rather than failing the run; use :func:`git_commit` where a
    provenance record without one should not be produced at all.
    """
    try:
        return git_commit(repo_root)
    except (OSError, subprocess.CalledProcessError):
        return None


def module_versions(*modules: ModuleType) -> dict[str, str]:
    """Return ``{module_name: module.__version__}`` for already-imported modules.

    Pass the imported modules themselves (``module_versions(np, pd, scipy)``)
    rather than names, since a study runner has already imported whatever it
    depends on.
    """
    return {module.__name__: module.__version__ for module in modules}


def package_versions(*names: str) -> dict[str, str]:
    """Return ``{name: version}`` for installed distributions, by package name.

    Unlike :func:`module_versions`, this reads installed package metadata
    directly, so it works for a dependency without a reliable
    ``__version__`` attribute and does not require importing it first.
    """
    return {name: _distribution_version(name) for name in names}


def git_status_clean(repo_root: Path | None = None) -> bool | None:
    """Whether the working tree has no uncommitted changes.

    ``None`` when the answer cannot be established, for the same reasons
    :func:`git_commit_or_none` returns ``None``. A provenance record that says
    ``False`` names a commit the outputs were not produced from exactly.
    """
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=repo_root or Path.cwd(),
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return status.strip() == ""
