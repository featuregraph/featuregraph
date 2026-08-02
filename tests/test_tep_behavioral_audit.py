import pandas as pd

from experiments.tep.behavioral_audit import (
    build_signatures,
    characterize_regimes,
    cliffs_delta,
    run_query_catalog,
    summarize_coverage,
    summarize_reproducibility,
)
from experiments.tep.compare_faults import FEATUREGRAPH_FEATURES


def _objects() -> pd.DataFrame:
    rows = []
    for fault in (1, 2):
        for run in range(1, 6):
            object_id = 0
            for regime, offset in (
                ("pre_injection", 0.0),
                ("early_response", 2.0 if fault == 1 else -1.0),
                ("post_response", 3.0 if fault == 1 else -2.0),
            ):
                for within_regime in range(3):
                    object_id += 1
                    row = {
                        "fault_number": fault,
                        "simulation_run": run,
                        "oscillation_id": object_id,
                        "regime": regime,
                        "start_index": object_id * 10,
                        "end_index": object_id * 10 + 9,
                    }
                    for index, property_name in enumerate(FEATUREGRAPH_FEATURES):
                        row[property_name] = index + within_regime + offset + 5.0
                    rows.append(row)
    return pd.DataFrame(rows)


def test_cliffs_delta_has_comparison_direction() -> None:
    assert cliffs_delta(pd.Series([1, 2]), pd.Series([3, 4])) == 1.0
    assert cliffs_delta(pd.Series([3, 4]), pd.Series([1, 2])) == -1.0


def test_characterization_and_reproducibility_preserve_runs() -> None:
    characterization = characterize_regimes(_objects())
    reproducibility = summarize_reproducibility(characterization)

    fault_one = reproducibility[
        reproducibility["fault_number"].eq(1)
        & reproducibility["regime"].eq("early_response")
        & reproducibility["property"].eq("amplitude")
    ].iloc[0]
    assert fault_one["runs_evaluated"] == 5
    assert fault_one["dominant_direction"] == "increase"
    assert fault_one["direction_consistency"] == 1.0
    assert bool(fault_one["repeatable"])


def test_query_catalog_answers_all_ten_questions() -> None:
    objects = _objects()
    characterization = characterize_regimes(objects)
    reproducibility = summarize_reproducibility(characterization)
    signatures = build_signatures(reproducibility)

    audit, results = run_query_catalog(objects, reproducibility, signatures)

    assert len(audit) == 10
    assert audit["answered"].all()
    assert set(results) == {f"Q{number:02d}" for number in range(1, 11)}


def test_coverage_includes_zero_object_regimes() -> None:
    objects = _objects()
    objects = objects.loc[
        ~(
            objects["fault_number"].eq(2)
            & objects["simulation_run"].eq(5)
            & objects["regime"].eq("post_response")
        )
    ]

    coverage = summarize_coverage(objects)
    missing = coverage[
        coverage["fault_number"].eq(2)
        & coverage["simulation_run"].eq(5)
        & coverage["regime"].eq("post_response")
    ].iloc[0]
    assert missing["complete_object_count"] == 0
    assert not bool(missing["has_complete_objects"])
