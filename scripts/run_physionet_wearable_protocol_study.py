"""Run the PhysioNet wearable stress-protocol representation study.

The protocol labels and boundaries come from the dataset authors' notebook.
FeatureGraph does not infer stress from physiology in this study. It compiles
the declared protocol states, preserves their tag boundaries, and measures the
native Empatica signals within those externally declared occurrences.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd

import featuregraph as fg

BASE_URL = (
    "https://physionet.org/files/wearable-device-dataset/1.0.1"
)
SUBJECTS = [*(f"S{i:02d}" for i in range(1, 19)), *(f"f{i:02d}" for i in range(1, 19))]
SIGNALS = ("HR", "EDA", "TEMP")
EXCLUSIONS = {
    "S02": "duplicated raw signals documented by the dataset authors",
    "f07": "PPG and temperature sensors covered by the protection dock",
    "f14": "protocol split across f14_a and f14_b after Bluetooth loss",
}

# Zero-based indices into each subject's tags.csv. These intervals reproduce
# the task spans shaded by the source notebook and add its declared baseline
# and rest phases. Interstitial reporting/setup time remains unassigned.
PROTOCOLS = {
    "v1": [
        ("baseline", 0, 1),
        ("stroop", 2, 3),
        ("first_rest", 3, 4),
        ("tmct", 4, 5),
        ("second_rest", 5, 6),
        ("real_opinion", 6, 7),
        ("opposite_opinion", 8, 9),
        ("subtract", 10, 11),
    ],
    "v2": [
        ("baseline", 0, 1),
        ("tmct", 1, 2),
        ("first_rest", 2, 3),
        ("real_opinion", 3, 4),
        ("opposite_opinion", 5, 6),
        ("second_rest", 6, 7),
        ("subtract", 7, 8),
    ],
}
SELF_REPORT_COLUMNS = {
    "v1": {
        "Baseline": "baseline",
        "Stroop": "stroop",
        "First Rest": "first_rest",
        "TMCT": "tmct",
        "Second Rest": "second_rest",
        "Real Opinion": "real_opinion",
        "Opposite Opinion": "opposite_opinion",
        "Subtract": "subtract",
    },
    "v2": {
        "Baseline": "baseline",
        "TMCT": "tmct",
        "First Rest": "first_rest",
        "Real Opinion": "real_opinion",
        "Opposite Opinion": "opposite_opinion",
        "Second Rest": "second_rest",
        "Subtract": "subtract",
    },
}
STATE_CONTRACT = {
    "version": "state-contract-v1",
    "state_column": "protocol_state",
    "group_by": "subject_id",
    "events": {
        "enter_protocol_state": {"type": "enter_label"},
        "exit_protocol_state": {"type": "exit_label"},
    },
}


@dataclass(frozen=True)
class SourceFile:
    relative_path: str
    local_path: Path


def cohort_for(subject_id: str) -> str:
    return "v1" if subject_id.startswith("S") else "v2"


def source_files(cache: Path) -> list[SourceFile]:
    files = [
        SourceFile(f"Stress_Level_{cohort}.csv", cache / f"Stress_Level_{cohort}.csv")
        for cohort in ("v1", "v2")
    ]
    for subject_id in SUBJECTS:
        source_subject = subject_id
        if subject_id == "f14":
            continue
        for filename in ("tags.csv", *(f"{signal}.csv" for signal in SIGNALS)):
            relative = f"Wearable_Dataset/STRESS/{source_subject}/{filename}"
            files.append(SourceFile(relative, cache / relative))
    return files


def download_one(source: SourceFile) -> None:
    if source.local_path.exists() and source.local_path.stat().st_size:
        return
    source.local_path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(f"{BASE_URL}/{source.relative_path}", timeout=180) as response:
        payload = response.read()
    source.local_path.write_bytes(payload)


def download_sources(cache: Path, workers: int = 8) -> None:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(download_one, source_files(cache)))


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


def declared_intervals(subject_id: str, tags: pd.DatetimeIndex) -> pd.DataFrame:
    cohort = cohort_for(subject_id)
    required = max(end for _, _, end in PROTOCOLS[cohort]) + 1
    if len(tags) < required:
        raise ValueError(
            f"{subject_id} has {len(tags)} tags; {required} are required for {cohort}."
        )
    rows = []
    for order, (state, start_index, end_index) in enumerate(PROTOCOLS[cohort]):
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
    subject_id: str, tags: pd.DatetimeIndex, intervals: pd.DataFrame
) -> pd.DataFrame:
    timestamps = pd.date_range(tags[0].floor("s"), tags[-1].ceil("s"), freq="1s")
    state = pd.Series("unassigned", index=timestamps, dtype="object")
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


def compiled_objects(compiled: pd.DataFrame) -> pd.DataFrame:
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
    objects["end_time"] = objects["end_sample_time"] + pd.Timedelta(seconds=1)
    objects["duration_seconds"] = objects["sample_count"].astype(float)
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


def read_self_reports(cache: Path) -> pd.DataFrame:
    rows = []
    for cohort in ("v1", "v2"):
        wide = pd.read_csv(cache / f"Stress_Level_{cohort}.csv", index_col=0)
        long = (
            wide.rename(columns=SELF_REPORT_COLUMNS[cohort])
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
    signal_rows: pd.DataFrame, intervals: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    for interval in intervals.itertuples(index=False):
        values = signal_rows.loc[
            (signal_rows["timestamp"] >= interval.start_time)
            & (signal_rows["timestamp"] < interval.end_time),
            "value",
        ].dropna()
        rows.append(
            {
                "subject_id": interval.subject_id,
                "protocol_state": interval.protocol_state,
                "signal": signal_rows["signal"].iloc[0],
                "signal_samples": len(values),
                "signal_mean": values.mean(),
                "signal_median": values.median(),
                "signal_min": values.min(),
                "signal_max": values.max(),
            }
        )
    return pd.DataFrame(rows)


def validation_row(check: str, passed: bool, details: str) -> dict[str, object]:
    return {"check": check, "passed": bool(passed), "details": details}


def run_study(cache: Path) -> dict[str, pd.DataFrame]:
    eligible = [subject for subject in SUBJECTS if subject not in EXCLUSIONS]
    declared_parts = []
    timeline_parts = []
    signal_parts = []
    compiler_reports = []

    for subject_id in eligible:
        base = cache / "Wearable_Dataset" / "STRESS" / subject_id
        tags = read_tags(base / "tags.csv")
        intervals = declared_intervals(subject_id, tags)
        timeline = protocol_timeline(subject_id, tags, intervals)
        compiled = fg.compile_states(timeline, STATE_CONTRACT)
        declared_parts.append(intervals)
        timeline_parts.append(compiled.observations)
        report = compiled.validation_report.copy()
        report["subject_id"] = subject_id
        compiler_reports.append(report)
        for signal in SIGNALS:
            native = read_empatica_signal(base / f"{signal}.csv", signal)
            signal_parts.append(aggregate_signal(native, intervals))

    declared = pd.concat(declared_parts, ignore_index=True)
    compiled = pd.concat(timeline_parts, ignore_index=True)
    objects = compiled_objects(compiled)
    mapped = match_declared_to_compiled(declared, objects)
    signal_summary = pd.concat(signal_parts, ignore_index=True)
    self_reports = read_self_reports(cache)
    self_reports = self_reports[self_reports["subject_id"].isin(eligible)].copy()
    study_objects = (
        mapped.merge(
            self_reports,
            on=["subject_id", "cohort", "protocol_state"],
            how="left",
            validate="one_to_one",
        )
        .merge(
            signal_summary.pivot(
                index=["subject_id", "protocol_state"],
                columns="signal",
                values=[
                    "signal_samples",
                    "signal_mean",
                    "signal_median",
                    "signal_min",
                    "signal_max",
                ],
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

    expected_objects = sum(
        len(PROTOCOLS[cohort_for(subject)]) for subject in eligible
    )
    schema_by_cohort = {
        cohort: tuple(study_objects[study_objects["cohort"] == cohort].columns)
        for cohort in ("v1", "v2")
    }
    checks = [
        validation_row(
            "eligible_subjects",
            len(eligible) == 33,
            f"eligible={len(eligible)} excluded={len(EXCLUSIONS)}",
        ),
        validation_row(
            "declared_object_count",
            len(study_objects) == expected_objects,
            f"objects={len(study_objects)} expected={expected_objects}",
        ),
        validation_row(
            "external_boundary_roundtrip",
            mapped["boundary_exact"].all(),
            f"exact={int(mapped['boundary_exact'].sum())}/{len(mapped)}",
        ),
        validation_row(
            "positive_durations",
            study_objects["duration_seconds_declared"].gt(0).all(),
            "all declared intervals have positive duration",
        ),
        validation_row(
            "self_report_interoperability",
            study_objects["self_reported_stress"].notna().all(),
            f"joined={int(study_objects['self_reported_stress'].notna().sum())}/{len(study_objects)}",
        ),
        validation_row(
            "native_signal_coverage",
            study_objects[[f"{signal.lower()}_samples" for signal in SIGNALS]]
            .gt(0)
            .all()
            .all(),
            "HR, EDA, and TEMP contain samples in every declared object",
        ),
        validation_row(
            "cross_protocol_schema",
            schema_by_cohort["v1"] == schema_by_cohort["v2"],
            "v1 and v2 use the same object schema and measurement equations",
        ),
        validation_row(
            "compiler_checks",
            pd.concat(compiler_reports)["passed"].all(),
            f"checks={len(pd.concat(compiler_reports))}",
        ),
    ]
    validation = pd.DataFrame(checks)
    if not validation["passed"].all():
        failed = validation.loc[~validation["passed"], "check"].tolist()
        raise AssertionError(f"Study validation failed: {failed}")

    state_summary = (
        study_objects.groupby(["cohort", "protocol_state"], sort=False)
        .agg(
            participants=("subject_id", "nunique"),
            median_duration_seconds=("duration_seconds_declared", "median"),
            median_self_reported_stress=("self_reported_stress", "median"),
            median_hr=("hr_median", "median"),
            median_eda=("eda_median", "median"),
            median_temperature=("temp_median", "median"),
        )
        .reset_index()
    )
    comparison = study_objects.assign(
        stage_kind=study_objects["protocol_state"].map(
            lambda state: (
                "rest_baseline"
                if state in {"baseline", "first_rest", "second_rest"}
                else "task"
            )
        )
    )
    participant_stage_means = (
        comparison.groupby(["subject_id", "cohort", "stage_kind"])
        .agg(
            self_reported_stress=("self_reported_stress", "mean"),
            hr=("hr_median", "mean"),
            eda=("eda_median", "mean"),
            temperature=("temp_median", "mean"),
        )
        .unstack("stage_kind")
    )
    contrast_rows = []
    for measure in ("self_reported_stress", "hr", "eda", "temperature"):
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
        compiled.assign(is_unassigned=compiled["state"].eq("unassigned"))
        .assign(cohort=compiled["subject_id"].map(cohort_for))
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
        "compiler_validation": pd.concat(compiler_reports, ignore_index=True),
        "compiled_timeline": compiled,
    }


def write_outputs(results: dict[str, pd.DataFrame], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, frame in results.items():
        frame.to_csv(output / f"{name}.csv.gz", index=False, compression="gzip")
    provenance = {
        "dataset": (
            "Wearable Device Dataset from Induced Stress and Structured "
            "Exercise Sessions"
        ),
        "dataset_version": "1.0.1",
        "dataset_doi": "10.13026/he0v-tf17",
        "source_url": "https://physionet.org/content/wearable-device-dataset/1.0.1/",
        "contract": STATE_CONTRACT,
        "protocols": PROTOCOLS,
        "signals": SIGNALS,
        "exclusions": EXCLUSIONS,
        "interpretation_boundary": (
            "Protocol states are externally declared. FeatureGraph does not infer "
            "stress or establish physiological validity."
        ),
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path("data/physionet_wearable"))
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/physionet_wearable_protocol")
    )
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    download_sources(args.cache, workers=args.workers)
    results = run_study(args.cache)
    write_outputs(results, args.output)
    print(results["validation"].to_string(index=False))
    print("\nState summary")
    print(results["state_summary"].to_string(index=False))


if __name__ == "__main__":
    main()
