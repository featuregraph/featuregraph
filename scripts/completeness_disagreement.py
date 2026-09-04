"""Run the completeness-disagreement eval: does a model know what it left out?

For each reference intake under ``artifacts/studies/completeness_disagreement/
reference``, the brief is rendered as prose and ablated: once whole, once
per withheld field, once per flattened rule. Each brief goes to the chosen
model twice, for the intake and then for the model's own account of what
is outstanding. The intake is the oracle; the account is scored against it.

One row per case goes to ``cases.csv`` under the output directory, with the
full record of every case in ``cases/<case>.json``. Provider credentials
come from the environment: ``COHERE_API_KEY`` or ``ANTHROPIC_API_KEY``.

Usage::

    python -m scripts.completeness_disagreement --provider offline
    python -m scripts.completeness_disagreement --provider anthropic \\
        --model claude-opus-5 --output outputs/completeness/anthropic
    python -m scripts.completeness_disagreement --provider cohere \\
        --model command-a-plus-05-2026 --only bidmc_respiration
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from featuregraph.study_builder.briefs import BriefCase, ablations  # noqa: E402
from featuregraph.study_builder.elicitation import (  # noqa: E402
    AnthropicElicitor,
    CohereElicitor,
    Elicitor,
    OfflineElicitor,
    elicit,
)
from featuregraph.study_builder.intake import (  # noqa: E402
    FIELDS,
    StudyIntake,
)
from featuregraph.study_builder.self_report import score  # noqa: E402

STUDY = ROOT / "artifacts" / "studies" / "completeness_disagreement"
REFERENCE = STUDY / "reference"
OUTPUT = ROOT / "outputs" / "completeness_disagreement"


def load_references(directory: Path = REFERENCE) -> dict[str, StudyIntake]:
    references = {}
    for path in sorted(directory.glob("*.json")):
        references[path.stem] = StudyIntake.from_payload(json.loads(path.read_text()))
    if not references:
        raise FileNotFoundError(f"no reference intakes under {directory}")
    return references


def _honest_offline(prompt: str, schema: Mapping[str, Any]) -> dict[str, Any]:
    """An elicitor that declares nothing and says so: the floor of the eval."""
    if "believed_missing" in schema.get("properties", {}):
        return {
            "believed_missing": [f.name for f in FIELDS],
            "believed_unstructured": [],
            "believed_ready": False,
        }
    return {f.name: None for f in FIELDS}


def make_elicitor(provider: str, model: str | None) -> Elicitor:
    if provider == "offline":
        return OfflineElicitor(_honest_offline, name=model or "offline-honest")
    if provider == "cohere":
        key = os.environ.get("COHERE_API_KEY", "")
        return CohereElicitor(key, model or "command-a-plus-05-2026")
    if provider == "anthropic":
        return AnthropicElicitor(model or "claude-opus-5")
    raise ValueError(f"unknown provider {provider!r}")


def run_case(case: BriefCase, elicitor: Elicitor) -> dict[str, Any]:
    result = elicit(case.text, elicitor)
    record: dict[str, Any] = {
        "case_id": case.case_id,
        "reference": case.reference,
        "withheld": list(case.withheld),
        "flattened": list(case.flattened),
        "model": elicitor.name,
        "brief_sha256": hashlib.sha256(case.text.encode()).hexdigest(),
        "intake_provenance": dict(result.intake_provenance),
        "claim_provenance": dict(result.claim_provenance),
        "error": result.error,
        "intake": result.intake_payload,
        "claim": result.claim.to_payload() if result.claim else None,
        "score": None,
    }
    if result.error is None and result.intake is not None and result.claim is not None:
        record["score"] = score(result.intake, result.claim, withheld=case.withheld)
    return record


def row(record: Mapping[str, Any]) -> dict[str, Any]:
    s = record["score"] or {}
    derived = s.get("derived", {})
    readiness = s.get("readiness", {})
    by_tier = s.get("overclaimed_by_tier", {})
    return {
        "case_id": record["case_id"],
        "reference": record["reference"],
        "model": record["model"],
        "withheld": ";".join(record["withheld"]),
        "flattened": ";".join(record["flattened"]),
        "failed": record["error"] is not None,
        "derived_unset": len(derived.get("unset", [])),
        "derived_unstructured": len(derived.get("unstructured", [])),
        "derived_approvable": derived.get("approvable"),
        "claimed_ready": readiness.get("claimed"),
        "false_ready": readiness.get("false_ready"),
        "overclaimed": len(s.get("overclaimed", [])),
        "overclaimed_compilable": len(by_tier.get("compilable", [])),
        "overclaimed_approvable": len(by_tier.get("approvable", [])),
        "underclaimed": len(s.get("underclaimed", [])),
        "shape_blind": len(s.get("shape_blind", [])),
        "fabricated": len(s.get("fabricated", [])),
        "agrees_exactly": s.get("agrees_exactly"),
        "overclaimed_fields": ";".join(s.get("overclaimed", [])),
        "underclaimed_fields": ";".join(s.get("underclaimed", [])),
        "fabricated_fields": ";".join(s.get("fabricated", [])),
    }


def summarise(table: pd.DataFrame) -> str:
    scored = table[~table["failed"]]
    if scored.empty:
        return f"{len(table)} cases, none scored"
    lines = [
        f"cases: {len(table)}, failed: {int(table['failed'].sum())}",
        f"exact agreement: {int(scored['agrees_exactly'].sum())} of {len(scored)}",
        f"cases with overclaiming: {int((scored['overclaimed'] > 0).sum())}",
        f"cases with underclaiming: {int((scored['underclaimed'] > 0).sum())}",
        f"cases with shape blindness: {int((scored['shape_blind'] > 0).sum())}",
        f"false ready: {int(scored['false_ready'].fillna(False).astype(bool).sum())}",
    ]
    withheld = scored[scored["withheld"] != ""]
    if len(withheld):
        lines.append(
            f"withheld-field cases: {len(withheld)}, fabricated the withheld "
            f"field in {int((withheld['fabricated'] > 0).sum())}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--provider", choices=["offline", "cohere", "anthropic"], required=True
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--reference-dir", type=Path, default=REFERENCE)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--only", action="append", default=[], help="reference stem")
    parser.add_argument("--full-only", action="store_true", help="skip the ablations")
    args = parser.parse_args(argv)

    elicitor = make_elicitor(args.provider, args.model)
    output = args.output or OUTPUT / elicitor.name.replace(":", "_").replace("/", "_")
    (output / "cases").mkdir(parents=True, exist_ok=True)

    references = load_references(args.reference_dir)
    records = []
    for name, intake in references.items():
        if args.only and name not in args.only:
            continue
        for case in ablations(name, intake):
            if args.full_only and (case.withheld or case.flattened):
                continue
            record = run_case(case, elicitor)
            records.append(record)
            path = output / "cases" / (case.case_id.replace("/", "__") + ".json")
            path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
            status = "failed" if record["error"] else "ok"
            print(f"{case.case_id}: {status}")

    table = pd.DataFrame([row(r) for r in records])
    table.to_csv(output / "cases.csv", index=False)
    (output / "run.json").write_text(
        json.dumps(
            {
                "model": elicitor.name,
                "run_at": datetime.now(timezone.utc).isoformat(),
                "references": sorted(references),
                "cases": len(records),
            },
            indent=1,
        )
        + "\n"
    )
    print()
    print(summarise(table))
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
