"""Write study results to disk in the shapes runners and reports expect."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd


def write_frames(
    frames: Mapping[str, pd.DataFrame],
    directory: Path,
    *,
    compression: str | None = "gzip",
) -> None:
    """Write each named frame as CSV under ``directory``.

    With ``compression="gzip"`` (the default) each file is
    ``<directory>/<name>.csv.gz``; with ``compression=None`` it is
    ``<directory>/<name>.csv``.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    suffix = ".csv.gz" if compression else ".csv"
    for name, frame in frames.items():
        frame.to_csv(
            directory / f"{name}{suffix}", index=False, compression=compression
        )


def write_json(
    path: Path,
    value: Any,
    *,
    indent: int = 2,
    sort_keys: bool = False,
    encoding: str | None = None,
) -> None:
    """Write one JSON-serializable value, matching a study's recorded formatting."""
    Path(path).write_text(
        json.dumps(value, indent=indent, sort_keys=sort_keys) + "\n",
        encoding=encoding,
    )


def write_csv_shards(
    frame: pd.DataFrame,
    directory: Path,
    *,
    stem: str,
    rows_per_shard: int = 3_000,
) -> list[str]:
    """Split a large frame into fixed-size CSV shards for publication.

    Returns the shard filenames in order, so a caller can reference them in a
    report without recomputing the split.
    """
    directory = Path(directory)
    names = []
    for part, start in enumerate(range(0, len(frame), rows_per_shard), start=1):
        name = f"{stem}_part_{part:03d}.csv"
        frame.iloc[start : start + rows_per_shard].to_csv(directory / name, index=False)
        names.append(name)
    return names


def markdown_table(frame: pd.DataFrame) -> str:
    """Render a frame as a GitHub-flavored Markdown table for a study report."""
    headers = [str(column) for column in frame.columns]
    rows = [
        [str(value) for value in row]
        for row in frame.itertuples(index=False, name=None)
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)
