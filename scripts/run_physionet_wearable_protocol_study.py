"""Run the PhysioNet wearable stress-protocol representation study.

The protocol labels and boundaries come from the dataset authors' notebook.
FeatureGraph does not infer stress from physiology in this study. It compiles
the declared protocol states, preserves their tag boundaries, and measures the
native Empatica signals within those externally declared occurrences.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.request import urlopen

import numpy as np
import pandas as pd

import featuregraph as fg
from featuregraph.studies import write_frames, write_json

DEFAULT_STUDY_CONTRACT_PATH = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "studies"
    / "physionet_wearable"
    / "study_contract.json"
)


def _require_contract(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"Invalid PhysioNet study contract: {message}")


def _protocols(contract: Mapping[str, Any]) -> dict[str, list[tuple[str, int, int]]]:
    result = {}
    for cohort, protocol in contract["protocol_versions"].items():
        result[cohort] = [
            (
                occurrence["state"],
                occurrence["start_tag_index"],
                occurrence["end_tag_index"],
            )
            for occurrence in protocol["occurrences"]
        ]
    return result


def _self_report_columns(contract: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    return {
        cohort: dict(protocol["self_report_columns"])
        for cohort, protocol in contract["protocol_versions"].items()
    }


def _subjects(contract: Mapping[str, Any]) -> list[str]:
    subjects: list[str] = []
    for cohort in contract["participant_cohorts"]:
        subjects.extend(
            f"{cohort['subject_prefix']}{number:02d}"
            for number in range(
                cohort["first_subject_number"],
                cohort["last_subject_number"] + 1,
            )
        )
    return subjects


def _exclusions(contract: Mapping[str, Any]) -> dict[str, str]:
    return {
        exclusion["subject_id"]: exclusion["reason"]
        for exclusion in contract["exclusions"]
    }


def _signal_files(contract: Mapping[str, Any]) -> dict[str, str]:
    return {
        signal["name"]: signal["file"]
        for signal in contract["sources"]["signals"]
    }


def _validate_physionet_contract(contract: Mapping[str, Any]) -> None:
    _require_contract(
        contract.get("contract_version") == "physionet-wearable-study-v1",
        "contract_version must be 'physionet-wearable-study-v1'",
    )
    _require_contract(
        contract.get("unresolved_questions") == [],
        "unresolved_questions must be empty before execution",
    )
    raw_cohorts = contract.get("participant_cohorts")
    _require_contract(
        isinstance(raw_cohorts, list) and bool(raw_cohorts), "missing cohorts"
    )
    cohorts = cast(list[dict[str, Any]], raw_cohorts)
    cohort_names = [cohort.get("cohort") for cohort in cohorts]
    prefixes = [cohort.get("subject_prefix") for cohort in cohorts]
    _require_contract(len(cohort_names) == len(set(cohort_names)), "duplicate cohorts")
    _require_contract(len(prefixes) == len(set(prefixes)), "duplicate prefixes")

    raw_protocols = contract.get("protocol_versions")
    _require_contract(
        isinstance(raw_protocols, dict)
        and set(raw_protocols) == set(cohort_names),
        "protocol versions must match participant cohorts",
    )
    protocols = cast(dict[str, dict[str, Any]], raw_protocols)
    declared_states: set[str] = set()
    for cohort, protocol in protocols.items():
        raw_occurrences = protocol.get("occurrences")
        _require_contract(
            isinstance(raw_occurrences, list) and bool(raw_occurrences),
            f"{cohort} must declare occurrences",
        )
        occurrences = cast(list[dict[str, Any]], raw_occurrences)
        raw_states = [occurrence.get("state") for occurrence in occurrences]
        _require_contract(
            all(isinstance(state, str) and state for state in raw_states),
            f"{cohort} states must be non-empty strings",
        )
        states = cast(list[str], raw_states)
        _require_contract(len(states) == len(set(states)), f"duplicate {cohort} states")
        for occurrence in occurrences:
            start = occurrence.get("start_tag_index")
            end = occurrence.get("end_tag_index")
            _require_contract(
                isinstance(start, int) and isinstance(end, int) and 0 <= start < end,
                f"invalid {cohort} tag interval",
            )
        report_columns = protocol.get("self_report_columns")
        _require_contract(
            isinstance(report_columns, dict)
            and set(report_columns.values()) == set(states),
            f"{cohort} self-report columns must map exactly to declared states",
        )
        declared_states.update(states)

    subjects = set(_subjects(contract))
    exclusions = _exclusions(contract)
    _require_contract(set(exclusions) <= subjects, "exclusions must name participants")
    _require_contract(
        all(reason.strip() for reason in exclusions.values()),
        "every exclusion must have a reason",
    )

    signals = _signal_files(contract)
    _require_contract(bool(signals), "at least one signal is required")
    _require_contract(
        all(name and filename for name, filename in signals.items()),
        "signal names and files must be non-empty",
    )
    statistics = contract.get("measurements", {}).get("statistics")
    supported_statistics = {"samples", "mean", "median", "min", "max"}
    _require_contract(
        isinstance(statistics, list)
        and set(statistics) <= supported_statistics
        and {"samples", "median"} <= set(statistics),
        "measurement statistics must be supported and include samples and median",
    )

    joins = contract.get("joins", {}).get("self_reports", {})
    _require_contract(
        joins.get("keys") == ["subject_id", "cohort", "protocol_state"],
        "self-report join keys must match the maintained object schema",
    )
    _require_contract(
        joins.get("cardinality") == "one_to_one",
        "self-report cardinality must be one_to_one",
    )

    raw_stage_kinds = contract.get("analysis", {}).get("stage_kinds")
    _require_contract(
        isinstance(raw_stage_kinds, dict), "stage kinds are required"
    )
    stage_kinds = cast(dict[str, list[str]], raw_stage_kinds)
    assigned_states = [state for states in stage_kinds.values() for state in states]
    _require_contract(
        len(assigned_states) == len(set(assigned_states)),
        "stage-kind states cannot overlap",
    )
    _require_contract(
        set(assigned_states) == declared_states,
        "stage kinds must cover every declared protocol state",
    )


APPROVED_STUDY_CONTRACT = fg.load_approved_study_contract(
    DEFAULT_STUDY_CONTRACT_PATH
)
STUDY_CONTRACT = APPROVED_STUDY_CONTRACT.contract
STUDY_CONTRACT_SHA256 = APPROVED_STUDY_CONTRACT.sha256
_validate_physionet_contract(STUDY_CONTRACT)

BASE_URL = STUDY_CONTRACT["dataset"]["base_url"]
SUBJECTS = _subjects(STUDY_CONTRACT)
SIGNAL_FILES = _signal_files(STUDY_CONTRACT)
SIGNALS = tuple(SIGNAL_FILES)
EXCLUSIONS = _exclusions(STUDY_CONTRACT)
PROTOCOLS = _protocols(STUDY_CONTRACT)
SELF_REPORT_COLUMNS = _self_report_columns(STUDY_CONTRACT)
STATE_CONTRACT = STUDY_CONTRACT["state_compiler"]
MEASUREMENT_STATISTICS = tuple(STUDY_CONTRACT["measurements"]["statistics"])


@dataclass(frozen=True)
class SourceFile:
    relative_path: str
    local_path: Path


def cohort_for(
    subject_id: str, contract: Mapping[str, Any] = STUDY_CONTRACT
) -> str:
    matches: list[str] = [
        str(cohort["cohort"])
        for cohort in contract["participant_cohorts"]
        if subject_id.startswith(cohort["subject_prefix"])
    ]
    if len(matches) != 1:
        raise ValueError(f"No unique cohort is declared for {subject_id!r}.")
    return matches[0]


def source_files(
    cache: Path, contract: Mapping[str, Any] = STUDY_CONTRACT
) -> list[SourceFile]:
    cohorts = [cohort["cohort"] for cohort in contract["participant_cohorts"]]
    self_report_template = contract["sources"]["self_report_file_template"]
    files = [
        SourceFile(
            self_report_template.format(cohort=cohort),
            cache / self_report_template.format(cohort=cohort),
        )
        for cohort in cohorts
    ]
    directory_template = contract["sources"]["subject_directory_template"]
    signal_files = _signal_files(contract)
    filenames = [contract["sources"]["tags_file"], *signal_files.values()]
    exclusions = _exclusions(contract)
    for subject_id in _subjects(contract):
        if subject_id in exclusions:
            continue
        for filename in filenames:
            relative = f"{directory_template.format(subject_id=subject_id)}/{filename}"
            files.append(SourceFile(relative, cache / relative))
    return files


def download_one(source: SourceFile, base_url: str = BASE_URL) -> None:
    if source.local_path.exists() and source.local_path.stat().st_size:
        return
    source.local_path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(f"{base_url}/{source.relative_path}", timeout=180) as response:
        payload = response.read()
    source.local_path.write_bytes(payload)


def download_sources(
    cache: Path,
    workers: int = 8,
    contract: Mapping[str, Any] = STUDY_CONTRACT,
) -> None:
    base_url = contract["dataset"]["base_url"]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(
            pool.map(
                lambda source: download_one(source, base_url),
                source_files(cache, contract),
            )
        )


def read_tags(path: Path) -> pd.DatetimeIndex:
    values = pd.read_csv(path, header=None)[0]
    return pd.DatetimeIndex(pd.to_datetime(values, utc=True))


def read_empatica_signal(path: Path, signal: str) -> pd.DataFrame:
    raw = pd.read_csv(path, header=None)
    start = pd.to_datetime(raw.iloc[0, 0], utc=True)
    rate_hz = float(raw.iloc[1, 0])
    values = pd.to_numeric(raw.iloc[2:, 0], errors="coerce").reset_index(drop=True)
    offsets = pd.to_timedelta(np.arange(len(values)) / rate_hz, unit="s")
    return pd.DataFrame(
        {
            "timestamp": start + offsets,
            "signal": signal,
            "value": values,
            "sampling_rate_hz": rate_hz,
        }
    )


def declared_intervals(
    subject_id: str,
    tags: pd.DatetimeIndex,
    contract: Mapping[str, Any] = STUDY_CONTRACT,
) -> pd.DataFrame:
    cohort = cohort_for(subject_id, contract)
    protocol = _protocols(contract)[cohort]
    required = max(end for _, _, end in protocol) + 1
    if len(tags) < required:
        raise ValueError(
            f"{subject_id} has {len(tags)} tags; {required} are required for {cohort}."
        )
    rows = []
    for order, (state, start_index, end_index) in enumerate(protocol):
        rows.append(
            {
                "subject_id": subject_id,
                "cohort": cohort,
                "protocol_order": order,
                "protocol_state": state,
                "start_tag_index": start_index,
                "end_tag_index": end_index,
                "start_time": tags[start_index],
                "end_time": tags[end_index],
            }
        )
    result = pd.DataFrame(rows)
    result["duration_seconds"] = (
        result["end_time"] - result["start_time"]
    ).dt.total_seconds()
    if not result["duration_seconds"].gt(0).all():
        raise ValueError(f"{subject_id} contains a non-positive declared interval.")
    return result


def protocol_timeline(
    subject_id: str,
    tags: pd.DatetimeIndex,
    intervals: pd.DataFrame,
    contract: Mapping[str, Any] = STUDY_CONTRACT,
) -> pd.DataFrame:
    sources = contract["sources"]
    if sources["interval_closure"] != "left":
        raise ValueError("Only left-closed protocol intervals are supported.")
    frequency = sources["timeline_frequency"]
    timestamps = pd.date_range(
        tags[0].floor(frequency), tags[-1].ceil(frequency), freq=frequency
    )
    state = pd.Series(sources["unassigned_label"], index=timestamps, dtype="object")
    for row in intervals.itertuples(index=False):
        state.loc[(state.index >= row.start_time) & (state.index < row.end_time)] = (
            row.protocol_state
        )
    return pd.DataFrame(
        {
            "subject_id": subject_id,
            "timestamp": timestamps,
            "protocol_state": state.to_numpy(),
        }
    )


def compiled_objects(
    compiled: pd.DataFrame, timeline_frequency: str = "1s"
) -> pd.DataFrame:
    objects = (
        compiled.groupby(
            ["subject_id", "state_occurrence_id", "state"], sort=False
        )
        .agg(
            start_time=("timestamp", "min"),
            end_sample_time=("timestamp", "max"),
            sample_count=("timestamp", "size"),
            enter_count=("enter_protocol_state", "sum"),
            exit_count=("exit_protocol_state", "sum"),
        )
        .reset_index()
        .rename(columns={"state": "protocol_state"})
    )
    sample_duration = pd.Timedelta(timeline_frequency)
    objects["end_time"] = objects["end_sample_time"] + sample_duration
    objects["duration_seconds"] = (
        objects["sample_count"].astype(float) * sample_duration.total_seconds()
    )
    return objects


def match_declared_to_compiled(
    declared: pd.DataFrame, objects: pd.DataFrame
) -> pd.DataFrame:
    mapped = declared.merge(
        objects,
        on=["subject_id", "protocol_state", "start_time", "end_time"],
        how="left",
        suffixes=("_declared", "_compiled"),
        validate="one_to_one",
    )
    mapped["boundary_exact"] = mapped["state_occurrence_id"].notna()
    return mapped


def read_self_reports(
    cache: Path, contract: Mapping[str, Any] = STUDY_CONTRACT
) -> pd.DataFrame:
    rows = []
    self_report_template = contract["sources"]["self_report_file_template"]
    mappings = _self_report_columns(contract)
    for cohort in mappings:
        source_path = cache / self_report_template.format(cohort=cohort)
        wide = pd.read_csv(source_path, index_col=0)
        long = (
            wide.rename(columns=mappings[cohort])
            .rename_axis("subject_id")
            .reset_index()
            .melt(
                id_vars="subject_id",
                var_name="protocol_state",
                value_name="self_reported_stress",
            )
        )
        long["cohort"] = cohort
        rows.append(long)
    return pd.concat(rows, ignore_index=True)


def aggregate_signal(
    signal_rows: pd.DataFrame,
    intervals: pd.DataFrame,
    statistics: tuple[str, ...] = MEASUREMENT_STATISTICS,
) -> pd.DataFrame:
    reducers = {
        "samples": lambda values: len(values),
        "mean": lambda values: values.mean(),
        "median": lambda values: values.median(),
        "min": lambda values: values.min(),
        "max": lambda values: values.max(),
    }
    rows = []
    for interval in intervals.itertuples(index=False):
        values = signal_rows.loc[
            (signal_rows["timestamp"] >= interval.start_time)
            & (signal_rows["timestamp"] < interval.end_time),
            "value",
        ].dropna()
        row = {
            "subject_id": interval.subject_id,
            "protocol_state": interval.protocol_state,
            "signal": signal_rows["signal"].iloc[0],
        }
        row.update(
            {
                f"signal_{statistic}": reducers[statistic](values)
                for statistic in statistics
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def validation_row(check: str, passed: bool, details: str) -> dict[str, object]:
    return {"check": check, "passed": bool(passed), "details": details}


def run_study(
    cache: Path,
    approved_contract: fg.ApprovedStudyContract = APPROVED_STUDY_CONTRACT,
) -> dict[str, pd.DataFrame]:
    contract = approved_contract.contract
    _validate_physionet_contract(contract)
    subjects = _subjects(contract)
    exclusions = _exclusions(contract)
    eligible = [subject for subject in subjects if subject not in exclusions]
    signal_files = _signal_files(contract)
    statistics = tuple(contract["measurements"]["statistics"])
    state_contract = contract["state_compiler"]
    directory_template = contract["sources"]["subject_directory_template"]
    declared_parts = []
    timeline_parts = []
    signal_parts = []
    compiler_reports = []

    for subject_id in eligible:
        base = cache / directory_template.format(subject_id=subject_id)
        tags = read_tags(base / contract["sources"]["tags_file"])
        intervals = declared_intervals(subject_id, tags, contract)
        timeline = protocol_timeline(subject_id, tags, intervals, contract)
        compiled = fg.compile_states(timeline, state_contract)
        declared_parts.append(intervals)
        timeline_parts.append(compiled.observations)
        report = compiled.validation_report.copy()
        report["subject_id"] = subject_id
        compiler_reports.append(report)
        for signal, filename in signal_files.items():
            native = read_empatica_signal(base / filename, signal)
            signal_parts.append(aggregate_signal(native, intervals, statistics))

    declared = pd.concat(declared_parts, ignore_index=True)
    compiled = pd.concat(timeline_parts, ignore_index=True)
    objects = compiled_objects(
        compiled, contract["sources"]["timeline_frequency"]
    )
    mapped = match_declared_to_compiled(declared, objects)
    signal_summary = pd.concat(signal_parts, ignore_index=True)
    self_reports = read_self_reports(cache, contract)
    self_reports = self_reports[self_reports["subject_id"].isin(eligible)].copy()
    join_keys = contract["joins"]["self_reports"]["keys"]
    signal_values = [f"signal_{statistic}" for statistic in statistics]
    study_objects = (
        mapped.merge(
            self_reports,
            on=join_keys,
            how="left",
            validate=contract["joins"]["self_reports"]["cardinality"],
        )
        .merge(
            signal_summary.pivot(
                index=["subject_id", "protocol_state"],
                columns="signal",
                values=signal_values,
            ).pipe(
                lambda frame: frame.set_axis(
                    [
                        f"{signal.lower()}_{measure.removeprefix('signal_')}"
                        for measure, signal in frame.columns
                    ],
                    axis=1,
                )
            ).reset_index(),
            on=["subject_id", "protocol_state"],
            how="left",
            validate="one_to_one",
        )
    )

    protocol_versions = _protocols(contract)
    contract_expected_objects = sum(
        len(protocol_versions[cohort_for(subject, contract)]) for subject in eligible
    )
    expectations = contract["validations"]
    expected_subjects = expectations["expected_eligible_subjects"]
    expected_objects = expectations["expected_declared_occurrences"]
    expected_compiler_checks = expectations["expected_compiler_checks"]
    cohort_names = [cohort["cohort"] for cohort in contract["participant_cohorts"]]
    schema_by_cohort = {
        cohort: tuple(study_objects[study_objects["cohort"] == cohort].columns)
        for cohort in cohort_names
    }
    compiler_validation = pd.concat(compiler_reports, ignore_index=True)
    checks = [
        validation_row(
            "eligible_subjects",
            len(eligible) == expected_subjects,
            (
                f"eligible={len(eligible)} excluded={len(exclusions)} "
                f"expected={expected_subjects}"
            ),
        ),
        validation_row(
            "declared_object_count",
            len(study_objects) == expected_objects
            and contract_expected_objects == expected_objects,
            (
                f"objects={len(study_objects)} expected={expected_objects} "
                f"derived_from_protocols={contract_expected_objects}"
            ),
        ),
        validation_row(
            "external_boundary_roundtrip",
            not expectations["require_exact_boundaries"]
            or mapped["boundary_exact"].all(),
            f"exact={int(mapped['boundary_exact'].sum())}/{len(mapped)}",
        ),
        validation_row(
            "positive_durations",
            not expectations["require_positive_durations"]
            or study_objects["duration_seconds_declared"].gt(0).all(),
            "all declared intervals have positive duration",
        ),
        validation_row(
            "self_report_interoperability",
            not expectations["require_complete_self_report_join"]
            or study_objects["self_reported_stress"].notna().all(),
            f"joined={int(study_objects['self_reported_stress'].notna().sum())}/{len(study_objects)}",
        ),
        validation_row(
            "native_signal_coverage",
            not expectations["require_native_signal_coverage"]
            or study_objects[
                [f"{signal.lower()}_samples" for signal in signal_files]
            ]
            .gt(0)
            .all()
            .all(),
            f"{', '.join(signal_files)} contain samples in every declared object",
        ),
        validation_row(
            "cross_protocol_schema",
            not expectations["require_cross_protocol_schema"]
            or len(set(schema_by_cohort.values())) == 1,
            "all protocol versions use one object schema and measurement equations",
        ),
        validation_row(
            "compiler_checks",
            compiler_validation["passed"].all()
            and len(compiler_validation) == expected_compiler_checks,
            (
                f"checks={len(compiler_validation)} "
                f"expected={expected_compiler_checks}"
            ),
        ),
    ]
    validation = pd.DataFrame(checks)
    if not validation["passed"].all():
        failed = validation.loc[~validation["passed"], "check"].tolist()
        raise AssertionError(f"Study validation failed: {failed}")

    signal_summary_aggregations = {
        f"median_{'temperature' if signal == 'TEMP' else signal.lower()}": (
            f"{signal.lower()}_median",
            "median",
        )
        for signal in signal_files
    }
    state_summary = (
        study_objects.groupby(["cohort", "protocol_state"], sort=False)
        .agg(
            participants=("subject_id", "nunique"),
            median_duration_seconds=("duration_seconds_declared", "median"),
            median_self_reported_stress=("self_reported_stress", "median"),
            **signal_summary_aggregations,
        )
        .reset_index()
    )
    stage_kind_by_state = {
        state: stage_kind
        for stage_kind, states in contract["analysis"]["stage_kinds"].items()
        for state in states
    }
    comparison = study_objects.assign(
        stage_kind=study_objects["protocol_state"].map(stage_kind_by_state)
    )
    contrast_measure_columns = {
        "self_reported_stress": "self_reported_stress",
        **{
            "temperature" if signal == "TEMP" else signal.lower(): (
                f"{signal.lower()}_median"
            )
            for signal in signal_files
        },
    }
    participant_stage_means = (
        comparison.groupby(["subject_id", "cohort", "stage_kind"])
        .agg(
            **{
                measure: (column, "mean")
                for measure, column in contrast_measure_columns.items()
            }
        )
        .unstack("stage_kind")
    )
    contrast_rows = []
    for measure in contrast_measure_columns:
        difference = (
            participant_stage_means[(measure, "task")]
            - participant_stage_means[(measure, "rest_baseline")]
        )
        contrast_rows.append(
            {
                "measure": measure,
                "participants": int(difference.notna().sum()),
                "median_task_minus_rest_baseline": difference.median(),
                "first_quartile": difference.quantile(0.25),
                "third_quartile": difference.quantile(0.75),
                "participants_with_positive_difference": int(
                    difference.gt(0).sum()
                ),
            }
        )
    contrast_summary = pd.DataFrame(contrast_rows)
    unassigned_summary = (
        compiled.assign(
            is_unassigned=compiled["state"].eq(
                contract["sources"]["unassigned_label"]
            )
        )
        .assign(
            cohort=compiled["subject_id"].map(
                lambda subject: cohort_for(subject, contract)
            )
        )
        .groupby("cohort")
        .agg(
            compiled_seconds=("is_unassigned", "size"),
            unassigned_seconds=("is_unassigned", "sum"),
        )
        .reset_index()
    )
    unassigned_summary["unassigned_fraction"] = (
        unassigned_summary["unassigned_seconds"]
        / unassigned_summary["compiled_seconds"]
    )
    return {
        "study_objects": study_objects,
        "state_summary": state_summary,
        "contrast_summary": contrast_summary,
        "unassigned_summary": unassigned_summary,
        "validation": validation,
        "compiler_validation": compiler_validation,
        "compiled_timeline": compiled,
    }


def write_outputs(
    results: dict[str, pd.DataFrame],
    output: Path,
    approved_contract: fg.ApprovedStudyContract = APPROVED_STUDY_CONTRACT,
) -> None:
    write_frames(results, output)
    contract = approved_contract.contract
    provenance = {
        "dataset": contract["dataset"],
        "study_contract": contract,
        "study_contract_sha256": approved_contract.sha256,
        "study_contract_source": str(approved_contract.source_path),
        "claim_boundaries": contract["claim_boundaries"],
    }
    write_json(output / "provenance.json", provenance)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path("data/physionet_wearable"))
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/physionet_wearable_protocol")
    )
    parser.add_argument(
        "--contract", type=Path, default=DEFAULT_STUDY_CONTRACT_PATH
    )
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    approved_contract = fg.load_approved_study_contract(args.contract)
    _validate_physionet_contract(approved_contract.contract)
    download_sources(
        args.cache,
        workers=args.workers,
        contract=approved_contract.contract,
    )
    results = run_study(args.cache, approved_contract)
    write_outputs(results, args.output, approved_contract)
    print(results["validation"].to_string(index=False))
    print("\nState summary")
    print(results["state_summary"].to_string(index=False))


if __name__ == "__main__":
    main()
