"""Focused tests for featuregraph.studies, the shared study-runner infrastructure."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from featuregraph.studies import (
    canonical_json,
    execute_notebook_sources,
    file_sha256,
    finite_summary,
    load_notebook_namespace,
    markdown_table,
    module_versions,
    notebook_sources,
    researcher_values,
    value_sha256,
    write_csv_shards,
    write_frames,
    write_json,
)


def _write_notebook(path: Path, code_cells: list[str]) -> None:
    notebook = {
        "cells": [
            {"cell_type": "code", "source": source.splitlines(keepends=True)}
            for source in code_cells
        ],
        "nbformat": 4,
    }
    path.write_text(json.dumps(notebook))


# --- notebooks -------------------------------------------------------------


def test_notebook_sources_returns_code_cells_in_order(tmp_path: Path) -> None:
    path = tmp_path / "study.ipynb"
    _write_notebook(path, ["a = 1\n", "b = 2\n"])

    assert notebook_sources(path) == ["a = 1\n", "b = 2\n"]


def test_researcher_values_evaluates_simple_assignments_only() -> None:
    source = """
import os
scope = {"dataset": "demo"}
threshold = 3
derived = threshold + 1
def helper():
    return 1
"""
    values = researcher_values(source)

    assert values["scope"] == {"dataset": "demo"}
    assert values["threshold"] == 3
    assert values["derived"] == 4
    assert "os" not in values
    assert "helper" not in values


def test_execute_notebook_sources_shares_namespace_and_captures_stdout() -> None:
    namespace, output = execute_notebook_sources(
        ["x = 1", "print(x)\ny = x + 1"],
        initial_namespace={"z": 10},
    )

    assert namespace["x"] == 1
    assert namespace["y"] == 2
    assert namespace["z"] == 10
    assert output == "1\n"


def test_load_notebook_namespace_stops_before_marker(tmp_path: Path) -> None:
    path = tmp_path / "generated.ipynb"
    _write_notebook(
        path,
        [
            "def double(value):\n    return value * 2\n",
            "# Subject 1 development record\nraise RuntimeError('must not run')",
        ],
    )

    namespace = load_notebook_namespace(
        path, stop_marker="# Subject 1 development record"
    )

    assert namespace["double"](21) == 42


# --- fingerprint -------------------------------------------------------------


def test_canonical_json_is_stable_under_key_reordering() -> None:
    first = {"b": 1, "a": {"y": 2, "x": 1}}
    second = {"a": {"x": 1, "y": 2}, "b": 1}

    assert canonical_json(first) == canonical_json(second)


def test_value_sha256_matches_reordered_equivalent_and_is_a_hex_digest() -> None:
    contract = {"version": "v1", "parameters": {"eps": 0.1, "window": 50}}
    reordered = json.loads(canonical_json(contract))

    digest = value_sha256(contract)
    assert digest == value_sha256(reordered)
    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)


def test_value_sha256_changes_when_a_leaf_value_changes() -> None:
    base = {"threshold": 1}
    changed = {"threshold": 2}

    assert value_sha256(base) != value_sha256(changed)


def test_file_sha256_matches_hashlib_reference(tmp_path: Path) -> None:
    import hashlib

    path = tmp_path / "input.ipynb"
    path.write_bytes(b"notebook bytes")

    assert file_sha256(path) == hashlib.sha256(b"notebook bytes").hexdigest()


# --- provenance --------------------------------------------------------------


def test_module_versions_reads_dunder_version_by_module_name() -> None:
    versions = module_versions(np, pd)

    assert versions == {"numpy": np.__version__, "pandas": pd.__version__}


# --- outputs -------------------------------------------------------------------


def test_write_frames_defaults_to_gzip(tmp_path: Path) -> None:
    write_frames({"objects": pd.DataFrame({"a": [1, 2]})}, tmp_path)

    written = tmp_path / "objects.csv.gz"
    assert written.exists()
    assert pd.read_csv(written)["a"].tolist() == [1, 2]


def test_write_frames_without_compression_writes_plain_csv(tmp_path: Path) -> None:
    write_frames(
        {"summary": pd.DataFrame({"a": [1]})}, tmp_path, compression=None
    )

    assert (tmp_path / "summary.csv").exists()
    assert not (tmp_path / "summary.csv.gz").exists()


def test_write_json_round_trips_and_respects_sort_keys(tmp_path: Path) -> None:
    path = tmp_path / "value.json"
    write_json(path, {"b": 1, "a": 2}, sort_keys=True)

    text = path.read_text()
    assert text.index('"a"') < text.index('"b"')
    assert json.loads(text) == {"b": 1, "a": 2}


def test_write_csv_shards_splits_by_row_count(tmp_path: Path) -> None:
    frame = pd.DataFrame({"value": range(7)})

    names = write_csv_shards(frame, tmp_path, stem="objects", rows_per_shard=3)

    assert names == [
        "objects_part_001.csv",
        "objects_part_002.csv",
        "objects_part_003.csv",
    ]
    shards = [pd.read_csv(tmp_path / name) for name in names]
    assert [len(shard) for shard in shards] == [3, 3, 1]
    assert pd.concat(shards, ignore_index=True)["value"].tolist() == list(range(7))


def test_markdown_table_renders_header_separator_and_rows() -> None:
    frame = pd.DataFrame({"subject": [1, 2], "count": [10, 20]})

    table = markdown_table(frame)

    lines = table.splitlines()
    assert lines[0] == "| subject | count |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| 1 | 10 |"
    assert lines[3] == "| 2 | 20 |"


# --- summaries -----------------------------------------------------------------


def test_finite_summary_drops_missing_and_infinite_values() -> None:
    values = pd.Series([1.0, 2.0, np.nan, np.inf, -np.inf, 3.0])

    summary = finite_summary(values)

    assert summary["count"] == 3
    assert summary["mean"] == pytest.approx(2.0)
    assert summary["minimum"] == 1.0
    assert summary["maximum"] == 3.0
