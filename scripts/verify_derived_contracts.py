"""Check that a contract carrying its own derivation reproduces a published one.

Two published constructions build their signal in pandas before anything
reaches the compiler: the BIDMC respiratory envelope and the TEP reactor
pressure envelope. Both are a rolling maximum, a rolling mean, a backward
shift and a first difference, and both then partition the difference into
rising, falling and inactive.

``artifacts/contracts/*_v2.json`` express the same constructions entirely
inside a ``state-contract-v2`` contract. This script runs both paths on the
same source records and compares them row by row:

- the *published path*: the preprocessing exactly as the researcher input
  and generated study write it, then the published state rules (the v1
  contract for BIDMC; the pandas state and event logic for TEP, which
  predates the compiler);
- the *declared path*: the raw observations and the v2 contract, nothing else.

It writes one row per record so a reader can check any single subject or
run rather than trust the aggregate, and exits non-zero on any mismatch.

BIDMC needs PhysioNet to be reachable, or the files already cached under
``~/.cache/featuregraph``. TEP downloads one workbook per run from GitHub.

Usage::

    python -m scripts.verify_derived_contracts --dataset tep
    python -m scripts.verify_derived_contracts --dataset bidmc --subjects 1,13
    python -m scripts.verify_derived_contracts --dataset all
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import featuregraph as fg
from featuregraph.studies import notebook_sources, researcher_values, value_sha256

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = REPO_ROOT / "artifacts" / "contracts"
DEFAULT_OUTPUT = CONTRACTS / "verification"
BIDMC_INPUT = (
    REPO_ROOT / "notebooks" / "researcher_input" / "bidmc_researcher_input.ipynb"
)
TEP_INPUT = REPO_ROOT / "notebooks" / "researcher_input" / "tep_researcher_input.ipynb"


def _envelope(series: pd.Series, max_window: int, mean_window: int, shift: int):
    return (
        series.rolling(max_window, min_periods=max_window)
        .max()
        .rolling(mean_window, min_periods=mean_window)
        .mean()
        .shift(shift)
    )


def _invalid_counts(details: str) -> dict[str, int]:
    return {key: int(value) for key, value in (p.split("=") for p in details.split())}


def _row(dataset: str, item: Any, compiled: fg.CompiledStateResult, checks: dict):
    report = compiled.validation_report.set_index("check")
    counts = _invalid_counts(report.loc["invalid_observations", "details"])
    observations = compiled.observations
    occurrences = int(report.loc["occurrence_reconstruction", "details"].split("=")[1])
    events = [name for name in compiled.contract["events"]]
    row = {
        "dataset": dataset,
        "item": item,
        "observations": len(observations),
        "valid_observations": int(observations["state_valid"].sum()),
        "excluded": counts["excluded"],
        "excluded_leading": counts["leading"],
        "excluded_trailing": counts["trailing"],
        "excluded_interior": counts["interior"],
        "occurrences": occurrences,
        "enter_events": int(observations[events[0]].sum()),
        "exit_events": int(observations[events[1]].sum()),
    }
    row.update({f"identical_{name}": bool(value) for name, value in checks.items()})
    row["identical"] = all(checks.values())
    return row


# -- BIDMC ------------------------------------------------------------------


def verify_bidmc_subject(subject: int, values: dict, contract: dict) -> dict:
    window = values["smooth_window"]
    raw = fg.datasets.bidmc(subject=subject).copy()
    raw["subject_id"] = subject

    # Published path, verbatim from the researcher input.
    prepared = raw.copy()
    prepared["respiration_smooth"] = _envelope(
        prepared["respiration"], window, window, -window
    )
    prepared["respiration_change"] = prepared["respiration_smooth"].diff()
    valid = (
        prepared["respiration_smooth"].notna() & prepared["respiration_change"].notna()
    )
    published = fg.compile_states(
        prepared.loc[valid, ["subject_id", "respiration_change"]],
        values["state_contract"],
    ).observations

    # Declared path: raw observations and the v2 contract.
    declared = fg.compile_states(raw[["subject_id", "respiration"]], contract)
    observations = declared.observations
    on_valid = observations.loc[valid]

    checks = {
        "valid_mask": observations["state_valid"].equals(valid),
        "derived_columns": (
            observations["respiration_smooth"].equals(prepared["respiration_smooth"])
            and observations["respiration_change"].equals(
                prepared["respiration_change"]
            )
        ),
        "states": on_valid["state"].tolist() == published["state"].tolist()
        and all(
            on_valid[f"state__{name}"].equals(published[f"state__{name}"])
            for name in ("rising", "falling", "inactive")
        ),
        "occurrence_ids": on_valid["state_occurrence_id"]
        .astype("int64")
        .equals(published["state_occurrence_id"]),
        "events": all(
            on_valid[name].equals(published[name])
            for name in ("enter_respiration_rising", "exit_respiration_rising")
        )
        and not observations.loc[
            ~valid, ["enter_respiration_rising", "exit_respiration_rising"]
        ]
        .any()
        .any(),
    }
    return _row("bidmc", subject, declared, checks)


# -- TEP --------------------------------------------------------------------


def verify_tep_run(run: int, parameters: dict, contract: dict) -> dict:
    max_window = parameters["rolling_max_window_samples"]
    mean_window = parameters["rolling_mean_window_samples"]
    shift = parameters["offline_alignment_shift_samples"]
    eps = parameters["rate_eps_pressure_units_per_hour"]

    raw = fg.datasets.eastman(fault_number=2, simulation_run=run).copy()
    raw["simulation_run"] = run

    # Published path, verbatim from the generated study. TEP predates the
    # compiler: its states and events are pandas expressions.
    time_hours = raw["time_(h)"]
    smooth = _envelope(raw["reactor_pressure"], max_window, mean_window, shift)
    change = smooth.diff()
    rate = change / time_hours.diff()
    valid = smooth.notna() & rate.notna()
    rising = valid & rate.gt(eps)
    falling = valid & rate.lt(-eps)
    inactive = valid & rate.abs().le(eps)
    transition_valid = valid & valid.shift(1, fill_value=False)
    rising_int = rising.astype(int)
    enter = transition_valid & rising_int.diff().eq(1)
    exit_after_peak = transition_valid & rising_int.diff().eq(-1)

    declared = fg.compile_states(
        raw[["simulation_run", "time_(h)", "reactor_pressure"]], contract
    )
    observations = declared.observations

    # The published exit sits on the first sample after the rising run; the
    # compiler's exit_state sits on the last rising sample. Same boundary,
    # one sample apart by convention.
    compiler_exit_shifted = (
        observations["exit_reactor_pressure_rising"].shift(1, fill_value=False)
    ).astype(bool)

    checks = {
        "valid_mask": observations["state_valid"].equals(valid),
        "derived_columns": (
            observations["reactor_pressure_smooth"].equals(smooth)
            and observations["reactor_pressure_change"].equals(change)
            and observations["reactor_pressure_rate"].equals(rate)
        ),
        "states": (
            observations["state__rising"].equals(rising)
            and observations["state__falling"].equals(falling)
            and observations["state__inactive"].equals(inactive)
        ),
        "events": (
            observations["enter_reactor_pressure_rising"].equals(enter)
            and compiler_exit_shifted.equals(exit_after_peak)
        ),
    }
    return _row("tep", run, declared, checks)


# -- driver -----------------------------------------------------------------


def _parse_ids(text: str | None, default: list[int]) -> list[int]:
    if not text:
        return default
    return [int(part) for part in text.split(",") if part.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dataset", choices=("bidmc", "tep", "all"), default="all")
    parser.add_argument("--subjects", help="BIDMC subjects, comma-separated")
    parser.add_argument("--runs", help="TEP Fault 2 simulation runs, comma-separated")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    contracts: dict[str, str] = {}

    if args.dataset in ("bidmc", "all"):
        values = researcher_values(notebook_sources(BIDMC_INPUT)[0])
        contract = json.loads(
            (CONTRACTS / "bidmc_respiration_states_v2.json").read_text()
        )
        contracts["bidmc_respiration_states_v2"] = value_sha256(contract)
        for subject in _parse_ids(args.subjects, values["subject_ids"]):
            row = verify_bidmc_subject(subject, values, contract)
            rows.append(row)
            print(f"bidmc subject {subject:>2}: identical={row['identical']}")

    if args.dataset in ("tep", "all"):
        parameters = researcher_values(notebook_sources(TEP_INPUT)[0])[
            "construction_parameters"
        ]
        contract = json.loads(
            (CONTRACTS / "tep_reactor_pressure_states_v2.json").read_text()
        )
        contracts["tep_reactor_pressure_states_v2"] = value_sha256(contract)
        for run in _parse_ids(args.runs, list(range(1, 11))):
            row = verify_tep_run(run, parameters, contract)
            rows.append(row)
            print(f"tep fault 2 run {run:>2}: identical={row['identical']}")

    table = pd.DataFrame(rows)
    stem = args.dataset if args.dataset != "all" else "all"
    table.to_csv(args.output_dir / f"{stem}_equivalence.csv", index=False)
    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "featuregraph_version": fg.__version__,
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "contract_sha256": contracts,
        "records": len(table),
        "records_identical": int(table["identical"].sum()),
        "excluded_interior_total": int(table["excluded_interior"].sum()),
    }
    (args.output_dir / f"{stem}_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))
    return 0 if bool(table["identical"].all()) else 1


if __name__ == "__main__":
    sys.exit(main())
