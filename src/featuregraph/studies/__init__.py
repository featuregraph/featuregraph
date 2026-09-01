"""Shared infrastructure for FeatureGraph study runners.

A study runner (``scripts/run_*.py``) turns a researcher-authored contract
into executed constructions, measurements, and a report. The scientific
content of each study is necessarily bespoke; the mechanics of binding
notebooks, fingerprinting declared values, capturing provenance, and writing
results are not. This package holds that mechanical layer so a new study
runner is contract, measurements, and report — not a reimplementation of
notebook loading and CSV writing.
"""

from .fingerprint import canonical_json, file_sha256, value_sha256
from .notebooks import (
    execute_notebook_sources,
    load_notebook_namespace,
    notebook_sources,
    researcher_values,
)
from .outputs import markdown_table, write_csv_shards, write_frames, write_json
from .provenance import (
    git_commit,
    git_commit_or_none,
    module_versions,
    package_versions,
)
from .summaries import finite_summary

__all__ = [
    "canonical_json",
    "execute_notebook_sources",
    "file_sha256",
    "finite_summary",
    "git_commit",
    "git_commit_or_none",
    "load_notebook_namespace",
    "markdown_table",
    "module_versions",
    "notebook_sources",
    "package_versions",
    "researcher_values",
    "value_sha256",
    "write_csv_shards",
    "write_frames",
    "write_json",
]
