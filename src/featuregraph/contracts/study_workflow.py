"""Shared binding and provenance helpers for paired FeatureGraph studies."""

from __future__ import annotations

import ast
import io
import json
from contextlib import redirect_stdout
from hashlib import sha256
from pathlib import Path
from typing import Any


def notebook_sources(path: Path) -> list[str]:
    """Return code-cell sources in notebook order."""
    notebook = json.loads(path.read_text())
    return [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_json(value: object) -> str:
    """Serialize a declarative artifact deterministically for hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def value_sha256(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def declarative_values(source: str, source_path: Path) -> dict[str, object]:
    """Evaluate only safe, declarative top-level assignments from Python source."""
    tree = ast.parse(source)
    values: dict[str, object] = {}
    safe_globals: dict[str, Any] = {
        "__builtins__": {},
        "dict": dict,
        "list": list,
        "range": range,
        "set": set,
        "tuple": tuple,
    }
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            expression = ast.Expression(node.value)
            value = eval(
                compile(expression, str(source_path), "eval"), safe_globals, values
            )
        except Exception:
            continue
        values[target.id] = value
    return values


def execute_notebook_sources(
    sources: list[str],
    source_path: Path,
    initial_namespace: dict[str, object] | None = None,
) -> tuple[dict[str, object], str]:
    """Execute notebook code cells in one namespace and capture text output."""
    namespace: dict[str, object] = {
        "__name__": "__main__",
        "display": lambda *values: None,
    }
    if initial_namespace:
        namespace.update(initial_namespace)
    output = io.StringIO()
    with redirect_stdout(output):
        for source in sources:
            exec(compile(source, str(source_path), "exec"), namespace)
    return namespace, output.getvalue()


def write_json_artifact(path: Path, value: object) -> str:
    """Write readable JSON and return the canonical-value fingerprint."""
    path.write_text(json.dumps(value, indent=2) + "\n")
    return value_sha256(value)
