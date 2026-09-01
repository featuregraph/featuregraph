"""Deterministic PhysioNet backend for the conversational Study Builder demo."""

from __future__ import annotations

import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

import featuregraph as fg
from featuregraph.studies import write_json
from featuregraph.study_builder import ExecutionReport
from scripts.run_physionet_wearable_protocol_study import (
    APPROVED_STUDY_CONTRACT,
    _exclusions,
    _protocols,
    _self_report_columns,
    _signal_files,
    _subjects,
    _validate_physionet_contract,
    cohort_for,
    run_study,
    write_outputs,
)


class PhysioNetConversationalDemoExecutor:
    """Run approved candidates against a protected, network-free fixture."""

    def __init__(self) -> None:
        self.reference_payload = fg.study_contract_payload(
            APPROVED_STUDY_CONTRACT.contract
        )

    def validate(self, candidate: dict[str, Any]) -> dict[str, bool]:
        """Validate the scientific boundary and the executable contract."""

        unexpected_candidate = deepcopy(candidate)
        unexpected_candidate["measurements"]["statistics"] = deepcopy(
            self.reference_payload["measurements"]["statistics"]
        )
        unexpected_differences = fg.study_contract_differences(
            unexpected_candidate,
            self.reference_payload,
        )
        executable = True
        try:
            _validate_physionet_contract(candidate)
        except (KeyError, TypeError, ValueError):
            executable = False
        return {
            "only_measurement_statistics_changed": not unexpected_differences,
            "physionet_contract_is_executable": executable,
            "no_unresolved_questions": candidate.get("unresolved_questions") == [],
        }

    def run(
        self,
        approved_contract: fg.ApprovedStudyContract,
        run_directory: Path,
    ) -> ExecutionReport:
        """Execute the approved contract and persist its deterministic tables."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            cache = Path(temporary_directory) / "protected_fixture"
            cache.mkdir()
            write_protected_fixture(cache, approved_contract.contract)
            results = run_study(cache, approved_contract)

        table_directory = run_directory / "tables"
        write_outputs(results, table_directory, approved_contract)
        _write_state_summary(results["state_summary"], run_directory)
        validation_rows = tuple(
            row._asdict() for row in results["validation"].itertuples(index=False)
        )
        output_files = tuple(
            str(path.relative_to(run_directory))
            for path in sorted(table_directory.iterdir())
            if path.is_file()
        )
        return ExecutionReport(
            eligible_participants=int(results["study_objects"]["subject_id"].nunique()),
            declared_occurrences=int(len(results["study_objects"])),
            compiler_checks=int(len(results["compiler_validation"])),
            all_checks_passed=bool(results["validation"]["passed"].all()),
            measurement_statistics=tuple(
                approved_contract.contract["measurements"]["statistics"]
            ),
            validation_rows=validation_rows,
            output_files=output_files,
        )


def write_protected_fixture(cache: Path, contract: dict[str, Any]) -> None:
    """Create structurally complete data without source participant values."""

    subjects = _subjects(contract)
    exclusions = _exclusions(contract)
    report_columns = _self_report_columns(contract)
    protocols = _protocols(contract)
    signal_files = _signal_files(contract)
    report_template = contract["sources"]["self_report_file_template"]
    directory_template = contract["sources"]["subject_directory_template"]

    for cohort, columns in report_columns.items():
        cohort_subjects = [
            subject for subject in subjects if cohort_for(subject, contract) == cohort
        ]
        reports = pd.DataFrame(
            {
                source_column: [float(index + 1)] * len(cohort_subjects)
                for index, source_column in enumerate(columns)
            },
            index=cohort_subjects,
        )
        reports.to_csv(cache / report_template.format(cohort=cohort))

    for subject_id in subjects:
        if subject_id in exclusions:
            continue
        cohort = cohort_for(subject_id, contract)
        required_tags = max(end for _, _, end in protocols[cohort]) + 1
        tags = pd.date_range(
            "2026-01-01",
            periods=required_tags,
            freq="1min",
            tz="UTC",
        )
        subject_directory = cache / directory_template.format(subject_id=subject_id)
        subject_directory.mkdir(parents=True)
        pd.Series(tags.astype(str)).to_csv(
            subject_directory / contract["sources"]["tags_file"],
            index=False,
            header=False,
        )
        sample_count = int((tags[-1] - tags[0]).total_seconds()) + 1
        for signal_index, filename in enumerate(signal_files.values(), start=1):
            _write_signal(
                subject_directory / filename,
                tags[0],
                sample_count,
                float(signal_index),
            )


def _write_signal(
    path: Path,
    start: pd.Timestamp,
    sample_count: int,
    value: float,
) -> None:
    rows = [start.isoformat(), "1.0", *([str(value)] * sample_count)]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_state_summary(state_summary: pd.DataFrame, run_directory: Path) -> None:
    headers = [str(column) for column in state_summary.columns]
    table = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in state_summary.itertuples(index=False, name=None):
        table.append(
            "| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |"
        )
    lines = [
        "# Generated state summary",
        "",
        "> Protected fixture output for workflow verification only.",
        "",
        *table,
    ]
    (run_directory / "state_summary.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def write_demo_manifest(path: Path, *, mode: str, model: str | None) -> None:
    """Write non-sensitive runtime provenance for the demonstration."""

    payload = {
        "interface": "FeatureGraph conversational study demo",
        "assistant_mode": mode,
        "model": model,
        "execution": "deterministic protected PhysioNet fixture",
        "commercial_llm_in_execution_path": False,
    }
    write_json(path, payload, encoding="utf-8")
