import pandas as pd
import pytest

from featuregraph.utils._eastman import (
    _relabel_faultfree_measurement_columns,
)
from featuregraph.utils._rename_map import eastman_map


def test_faultfree_measurements_use_xmeas_names_before_shared_rename():
    source_columns = [
        "time",
        *[f"xmv_{index}" for index in range(1, 42)],
    ]
    source = pd.DataFrame(
        [[0.0, *range(1, 42)]],
        columns=source_columns,
    )

    relabeled = _relabel_faultfree_measurement_columns(source)
    renamed = relabeled.rename(columns=eastman_map)

    assert renamed.loc[0, "reactor_pressure"] == 7
    assert renamed.loc[0, "reactor_temperature"] == 9
    assert renamed.loc[0, "separator_cooling_water_inlet_temp"] == 41
    assert "separator_underflow_valve" not in renamed.columns


def test_faulty_measurements_and_manipulated_variables_remain_distinct():
    source = pd.DataFrame(
        {
            "xmeas_7": [2800.0],
            "xmv_7": [65.0],
        }
    )

    renamed = source.rename(columns=eastman_map)

    assert renamed.loc[0, "reactor_pressure"] == 2800.0
    assert renamed.loc[0, "separator_underflow_valve"] == 65.0


def test_faultfree_relabel_rejects_an_unexpected_source_schema():
    source = pd.DataFrame({"time": [0.0], "xmv_1": [1.0]})

    with pytest.raises(
        ValueError,
        match="Unexpected fault-free Tennessee Eastman workbook schema",
    ):
        _relabel_faultfree_measurement_columns(source)
