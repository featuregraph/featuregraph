"""Reduce one completeness-eval run to the tables a report is written from.

Reads the per-case records ``scripts/completeness_disagreement.py`` writes,
one JSON per case, and produces:

- headline counts: cases, failed, exact agreement, false ready;
- one row per intake field: how often it was outstanding, how often the
  model said so, how often it was fabricated when withheld, how often it
  was declared unstructured and the model called it complete;
- the withheld-field table: for each withheld field, whether the model
  left it unset, declared it anyway, and whether it named it as missing.

Ground truth per case is the intake's own; the field table is where a
model's blind spots show, since a rate over 56 cases hides which fields
carry the disagreement.

Usage::

    python -m scripts.summarize_completeness_run RUN_DIR [RUN_DIR ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from featuregraph.study_builder.intake import FIELDS  # noqa: E402


def load_records(run_dir: Path) -> list[dict[str, Any]]:
    records = [
        json.loads(path.read_text())
        for path in sorted((run_dir / "cases").glob("*.json"))
    ]
    if not records:
        raise FileNotFoundError(f"no case records under {run_dir / 'cases'}")
    return records


def headline(records: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [r for r in records if r["score"] is not None]
    withheld = [r for r in scored if r["withheld"]]
    flattened = [r for r in scored if r["flattened"]]
    return {
        "model": records[0]["model"],
        "cases": len(records),
        "failed": len(records) - len(scored),
        "exact_agreement": sum(r["score"]["agrees_exactly"] for r in scored),
        "cases_overclaiming": sum(bool(r["score"]["overclaimed"]) for r in scored),
        "cases_underclaiming": sum(bool(r["score"]["underclaimed"]) for r in scored),
        "cases_shape_blind": sum(bool(r["score"]["shape_blind"]) for r in scored),
        "false_ready": sum(r["score"]["readiness"]["false_ready"] for r in scored),
        "claimed_ready": sum(r["score"]["readiness"]["claimed"] for r in scored),
        "derived_approvable": sum(r["score"]["derived"]["approvable"] for r in scored),
        "withheld_cases": len(withheld),
        "fabricated": sum(bool(r["score"]["fabricated"]) for r in withheld),
        "withheld_named_missing": sum(
            r["withheld"][0] in r["score"]["claimed"]["missing"] for r in withheld
        ),
        "flattened_cases": len(flattened),
        "flattened_unstructured": sum(
            r["flattened"][0] in r["score"]["derived"]["unstructured"]
            for r in flattened
        ),
        "flattened_shape_blind": sum(
            r["flattened"][0] in r["score"]["shape_blind"] for r in flattened
        ),
    }


def field_table(records: list[dict[str, Any]]) -> pd.DataFrame:
    counts: dict[str, Counter] = defaultdict(Counter)
    for r in records:
        s = r["score"]
        if s is None:
            continue
        outstanding = set(s["derived"]["unset"]) | set(s["derived"]["unstructured"])
        claimed = set(s["claimed"]["missing"]) | set(s["claimed"]["unstructured"])
        for f in FIELDS:
            c = counts[f.name]
            c["cases"] += 1
            if f.name in outstanding:
                c["outstanding"] += 1
                if f.name in claimed:
                    c["outstanding_and_named"] += 1
            if f.name in s["overclaimed"]:
                c["overclaimed"] += 1
            if f.name in s["underclaimed"]:
                c["underclaimed"] += 1
            if f.name in s["shape_blind"]:
                c["shape_blind"] += 1
            if f.name in s["withheld"]:
                c["withheld"] += 1
                if f.name in s["fabricated"]:
                    c["fabricated"] += 1
    rows = []
    for f in FIELDS:
        c = counts[f.name]
        rows.append(
            {
                "field": f.name,
                "tier": f.tier,
                "cases": c["cases"],
                "outstanding": c["outstanding"],
                "outstanding_and_named": c["outstanding_and_named"],
                "overclaimed": c["overclaimed"],
                "underclaimed": c["underclaimed"],
                "shape_blind": c["shape_blind"],
                "withheld": c["withheld"],
                "fabricated": c["fabricated"],
            }
        )
    return pd.DataFrame(rows)


def withheld_table(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for r in records:
        if not r["withheld"] or r["score"] is None:
            continue
        name = r["withheld"][0]
        s = r["score"]
        rows.append(
            {
                "case_id": r["case_id"],
                "reference": r["reference"],
                "withheld": name,
                "left_unset": name in s["derived"]["unset"],
                "fabricated": name in s["fabricated"],
                "named_missing": name in s["claimed"]["missing"],
                "claimed_ready": s["readiness"]["claimed"],
            }
        )
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run_dir", type=Path, nargs="+")
    args = parser.parse_args(argv)
    pd.set_option("display.width", 200)
    for run_dir in args.run_dir:
        records = load_records(run_dir)
        head = headline(records)
        fields = field_table(records)
        withheld = withheld_table(records)
        (run_dir / "summary.json").write_text(json.dumps(head, indent=1) + "\n")
        fields.to_csv(run_dir / "fields.csv", index=False)
        withheld.to_csv(run_dir / "withheld.csv", index=False)
        print(f"## {head['model']}")
        for key, value in head.items():
            if key != "model":
                print(f"- {key}: {value}")
        print()
        print(fields.to_string(index=False))
        print()
        print(f"wrote summary.json, fields.csv and withheld.csv under {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
