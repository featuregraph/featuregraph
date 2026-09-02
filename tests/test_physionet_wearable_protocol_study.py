from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

import featuregraph as fg
from scripts.run_physionet_wearable_protocol_study import (
    APPROVED_STUDY_CONTRACT,
    EXCLUSIONS,
    PROTOCOLS,
    SELF_REPORT_COLUMNS,
    SIGNAL_FILES,
    STATE_CONTRACT,
    STUDY_CONTRACT,
    STUDY_CONTRACT_SHA256,
    SUBJECTS,
    _validate_physionet_contract,
    cohort_for,
    compiled_objects,
    declared_intervals,
    match_declared_to_compiled,
    protocol_timeline,
    run_study,
    source_files,
)


def _tags(count: int) -> pd.DatetimeIndex:
    return pd.date_range("2026-01-01", periods=count, freq="1min", tz="UTC")


def _write_empatica_signal(
    path: Path, start: pd.Timestamp, sample_count: int, value: float
) -> None:
    rows = [start.isoformat(), "1.0", *([str(value)] * sample_count)]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_cohort_fixture(cache: Path) -> None:
    for cohort, columns in SELF_REPORT_COLUMNS.items():
        cohort_subjects = [
            subject for subject in SUBJECTS if cohort_for(subject) == cohort
        ]
        reports = pd.DataFrame(
            {
                source_column: [float(index + 1)] * len(cohort_subjects)
                for index, source_column in enumerate(columns)
            },
            index=cohort_subjects,
        )
        reports.to_csv(cache / f"Stress_Level_{cohort}.csv")

    for subject_id in SUBJECTS:
        if subject_id in EXCLUSIONS:
            continue
        cohort = cohort_for(subject_id)
        tag_count = max(end for _, _, end in PROTOCOLS[cohort]) + 1
        tags = _tags(tag_count)
        subject_dir = cache / "Wearable_Dataset" / "STRESS" / subject_id
        subject_dir.mkdir(parents=True)
        pd.Series(tags.astype(str)).to_csv(
            subject_dir / "tags.csv", index=False, header=False
        )
        sample_count = int((tags[-1] - tags[0]).total_seconds()) + 1
        for signal_index, filename in enumerate(SIGNAL_FILES.values(), start=1):
            _write_empatica_signal(
                subject_dir / filename,
                tags[0],
                sample_count,
                float(signal_index),
            )


def test_protocol_versions_have_stable_declared_schema() -> None:
    v1 = declared_intervals("S01", _tags(13))
    v2 = declared_intervals("f01", _tags(9))

    assert list(v1.columns) == list(v2.columns)
    assert v1["protocol_state"].tolist() == [row[0] for row in PROTOCOLS["v1"]]
    assert v2["protocol_state"].tolist() == [row[0] for row in PROTOCOLS["v2"]]


def test_external_boundaries_round_trip_through_compiler() -> None:
    tags = _tags(13)
    declared = declared_intervals("S01", tags)
    timeline = protocol_timeline("S01", tags, declared)
    compiled = fg.compile_states(timeline, STATE_CONTRACT).observations
    objects = compiled_objects(compiled)
    mapped = match_declared_to_compiled(declared, objects)

    assert mapped["boundary_exact"].all()
    assert "unassigned" in compiled["state"].unique()
    assert (
        compiled["enter_protocol_state"].sum() == compiled["exit_protocol_state"].sum()
    )


def test_protocol_rejects_missing_required_tags() -> None:
    try:
        declared_intervals("S01", _tags(5))
    except ValueError as error:
        assert "required" in str(error)
    else:
        raise AssertionError("Expected incomplete tags to be rejected")


def test_maintained_contract_is_approved_and_drives_runner_constants() -> None:
    assert APPROVED_STUDY_CONTRACT.sha256 == STUDY_CONTRACT_SHA256
    assert fg.study_contract_sha256(STUDY_CONTRACT) == STUDY_CONTRACT_SHA256
    assert STUDY_CONTRACT["validations"] == {
        "expected_eligible_subjects": 33,
        "expected_declared_occurrences": 248,
        "expected_compiler_checks": 99,
        "require_exact_boundaries": True,
        "require_positive_durations": True,
        "require_complete_self_report_join": True,
        "require_native_signal_coverage": True,
        "require_cross_protocol_schema": True,
    }


def test_runner_rejects_unresolved_contract_questions() -> None:
    candidate = deepcopy(STUDY_CONTRACT)
    candidate["unresolved_questions"] = ["Which boundary applies?"]

    with pytest.raises(ValueError, match="unresolved_questions must be empty"):
        _validate_physionet_contract(candidate)


def test_download_manifest_excludes_every_contract_exclusion(tmp_path) -> None:
    manifest = source_files(tmp_path)
    relative_paths = [source.relative_path for source in manifest]

    assert all(
        f"/{subject_id}/" not in path
        for subject_id in EXCLUSIONS
        for path in relative_paths
    )


def test_approved_contract_reproduces_protected_cohort_counts(tmp_path) -> None:
    _write_cohort_fixture(tmp_path)

    results = run_study(tmp_path)
    objects = results["study_objects"]
    compiler_validation = results["compiler_validation"]

    assert objects["subject_id"].nunique() == 33
    assert len(objects) == 248
    assert objects["boundary_exact"].all()
    assert objects["self_reported_stress"].notna().all()
    assert objects[["hr_samples", "eda_samples", "temp_samples"]].gt(0).all().all()
    assert len(compiler_validation) == 99
    assert compiler_validation["passed"].all()
    assert results["validation"]["passed"].all()
