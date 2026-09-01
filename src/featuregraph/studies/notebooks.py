"""Bind and execute researcher-input and generated-study notebooks.

A FeatureGraph study is authored as a paired notebook: a researcher-input
notebook that declares scope, parameters, and claim limits as plain Python
values, and a generated-study notebook that implements those declarations.
Runner scripts bind the two together, execute the generated notebook, and
compare its declared values against the researcher input. These helpers hold
that mechanical layer so it is written once.
"""

from __future__ import annotations

import ast
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any


def notebook_sources(path: Path) -> list[str]:
    """Return the source of every code cell in a notebook, in cell order."""
    notebook = json.loads(Path(path).read_text())
    return [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]


def researcher_values(source: str) -> dict[str, Any]:
    """Evaluate only declarative top-level assignments from a cell's source.

    Only simple ``name = <expression>`` assignments are evaluated, each in
    order against the values already bound. Anything else (imports, calls,
    control flow, multi-target assignment) is silently skipped, so this
    reads researcher declarations without executing study mechanics.
    """
    tree = ast.parse(source)
    values: dict[str, Any] = {}
    safe_globals = {"__builtins__": {}, "list": list, "range": range}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            expression = ast.Expression(node.value)
            value = eval(
                compile(expression, "<researcher_values>", "eval"),
                safe_globals,
                values,
            )
        except Exception:
            continue
        values[target.id] = value
    return values


def execute_notebook_sources(
    sources: list[str],
    initial_namespace: dict[str, Any] | None = None,
    *,
    filename: str = "<generated_study>",
) -> tuple[dict[str, Any], str]:
    """Execute notebook code cells in order into one shared namespace.

    Returns the final namespace and everything the cells printed, so a caller
    can both inspect study results and archive the console transcript.
    """
    namespace: dict[str, Any] = {"__name__": "__main__"}
    if initial_namespace:
        namespace.update(initial_namespace)
    output = io.StringIO()
    with redirect_stdout(output):
        for source in sources:
            exec(compile(source, filename, "exec"), namespace)
    return namespace, output.getvalue()


def load_notebook_namespace(
    path: Path,
    *,
    stop_marker: str | None = None,
    name: str = "__main__",
) -> dict[str, Any]:
    """Execute a notebook's code cells and return the resulting namespace.

    ``stop_marker`` truncates the concatenated source at its first
    occurrence before execution. This lets a runner reuse a generated
    study's function and constant definitions without re-running the
    development-record cells that follow them.
    """
    source = "\n\n".join(notebook_sources(path))
    if stop_marker is not None:
        source = source.split(stop_marker, 1)[0]
    namespace: dict[str, Any] = {"__name__": name}
    exec(compile(source, str(path), "exec"), namespace)
    return namespace
